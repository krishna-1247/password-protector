"""
run_and_test.py
---------------
Self-contained script that:
1. Starts the FastAPI backend as a subprocess (keeps it alive after script exits via Popen)
2. Waits for it to be healthy
3. Runs the complete end-to-end test
4. Leaves the server running

Run from: backend/
"""

import os
import pathlib
import subprocess
import sys
import time
import zipfile

import requests

ROOT = pathlib.Path(__file__).parent.parent
BACKEND = pathlib.Path(__file__).parent
PDFS = ROOT / "input"
EXCEL = ROOT / "passwords.xlsx"
OUT_ZIP = BACKEND / "e2e_output.zip"
EXTRACT = BACKEND / "e2e_extracted"

BASE = "http://localhost:8000/api/v1"

print("=" * 62)
print("  PDF Password Protector — Local Integration Test")
print("=" * 62)

# ── 0. Kill anything on 8000, then start fresh backend ─────────
print("\n[STEP 1] Starting FastAPI backend on port 8000...")

# Kill existing uvicorn on 8000 (Windows)
subprocess.run(
    'for /f "tokens=5" %a in (\'netstat -aon ^| findstr ":8000 "\') do taskkill /f /pid %a',
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(1)

env = os.environ.copy()
env["PYTHONPATH"] = str(BACKEND)

server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=str(BACKEND),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
print(f"  Uvicorn PID: {server.pid}")

# ── 1. Wait for healthy ─────────────────────────────────────────
print("\n[STEP 2] Waiting for backend health check...")
healthy = False
for i in range(20):
    time.sleep(1)
    try:
        r = requests.get("http://localhost:8000/health", timeout=2)
        if r.status_code == 200:
            print(f"  ✓ Backend healthy after {i+1}s: {r.json()}")
            healthy = True
            break
    except Exception:
        pass

if not healthy:
    # Print server output for debugging
    server.kill()
    out, _ = server.communicate(timeout=5)
    print("BACKEND FAILED. Output:")
    print(out)
    sys.exit(1)

# ── 2. Swagger / ReDoc ──────────────────────────────────────────
print("\n[STEP 3] Checking Swagger UI and ReDoc...")
for url, name in [
    ("http://localhost:8000/docs", "Swagger UI"),
    ("http://localhost:8000/redoc", "ReDoc"),
]:
    r = requests.get(url, timeout=5)
    status = "✓" if r.status_code == 200 else "✗"
    print(f"  {status} {name}: HTTP {r.status_code} ({url})")

# ── 3. Upload ───────────────────────────────────────────────────
print("\n[STEP 4] Uploading test PDFs + Excel...")
pdf_files = sorted(PDFS.glob("*.pdf"))
print(f"  Found {len(pdf_files)} PDF(s) in input/:")
for f in pdf_files:
    print(f"    • {f.name} ({f.stat().st_size:,} bytes)")

files = [("pdfs", (f.name, open(f, "rb"), "application/pdf")) for f in pdf_files]
files.append(
    (
        "excel",
        (
            EXCEL.name,
            open(EXCEL, "rb"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
)

t0 = time.time()
r = requests.post(f"{BASE}/upload", files=files, timeout=120)
r.raise_for_status()
upload = r.json()
job_id = upload["job_id"]
print(f"  ✓ Upload OK — job_id: {job_id}")
print(f"  ✓ Files: {upload['file_count']} PDFs + 1 Excel")

# ── 4. Process ──────────────────────────────────────────────────
print("\n[STEP 5] Starting encryption job...")
r = requests.post(
    f"{BASE}/process/{job_id}",
    json={"skip_encrypted": False, "overwrite": True, "max_workers": 4},
    timeout=10,
)
r.raise_for_status()
print(f"  ✓ {r.status_code} — {r.json()['message']}")

# ── 5. Poll ─────────────────────────────────────────────────────
print("\n[STEP 6] Polling job status...")
final = None
for i in range(60):
    time.sleep(1)
    r = requests.get(f"{BASE}/status/{job_id}", timeout=5)
    s = r.json()
    pct = s["progress"]
    done = s["done"]
    tot = s["total"]
    stat = s["status"]
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    sys.stdout.write(f"\r  [{i+1:02d}s] {stat:12s}  {pct:3d}% |{bar}|  {done}/{tot}   ")
    sys.stdout.flush()
    if stat in ("completed", "failed"):
        final = s
        print()
        break

if not final:
    print("\n  ✗ Timed out")
    server.kill()
    sys.exit(1)

elapsed = time.time() - t0
print(f"\n  Completed in {elapsed:.2f}s")
stats = final["stats"]
print(
    f"  total={stats['total']}  success={stats['success']}  "
    f"missing={stats['missing']}  failed={stats['failed']}  "
    f"skipped={stats['skipped']}"
)

if final["status"] == "failed":
    print(f"  ✗ Job FAILED: {final.get('error')}")
    server.kill()
    sys.exit(1)

# ── 6. Download ZIP ─────────────────────────────────────────────
print("\n[STEP 7] Downloading encrypted ZIP...")
r = requests.get(f"{BASE}/download/{job_id}", timeout=60, stream=True)
r.raise_for_status()
OUT_ZIP.write_bytes(r.content)
print(f"  ✓ ZIP size: {len(r.content):,} bytes  →  {OUT_ZIP.name}")

# ── 7. Extract + verify encryption ─────────────────────────────
print("\n[STEP 8] Verifying each PDF is encrypted...")
EXTRACT.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT_ZIP) as zf:
    names = zf.namelist()
    zf.extractall(EXTRACT)
print(f"  ZIP contains {len(names)} file(s): {', '.join(names)}")

from pypdf import PdfReader

ok = 0
fail_list = []
for name in names:
    path = EXTRACT / name
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        print(f"  ✓ {name}  — ENCRYPTED")
        ok += 1
    else:
        print(f"  ✗ {name}  — NOT encrypted!")
        fail_list.append(name)

if fail_list:
    print(f"\n  FAIL: {fail_list} not encrypted")
    server.kill()
    sys.exit(1)

# ── 8. Summary ──────────────────────────────────────────────────
print("\n" + "=" * 62)
print("  ALL TESTS PASSED ✓")
print("=" * 62)
print(f"  Backend:         http://localhost:8000  (PID {server.pid})")
print("  Swagger UI:      http://localhost:8000/docs")
print("  ReDoc:           http://localhost:8000/redoc")
print("  Frontend:        http://localhost:3000")
print(f"  PDFs encrypted:  {ok}/{len(names)}")
print(f"  ZIP saved:       {OUT_ZIP}")
print(f"  Elapsed:         {elapsed:.2f}s")
print("=" * 62)
print("\n  Backend server is still running — do NOT close this window.")
print("  Press Ctrl+C to stop.\n")

# Keep server alive indefinitely
try:
    server.wait()
except KeyboardInterrupt:
    print("\nStopping server...")
    server.terminate()
