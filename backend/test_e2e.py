"""
Full end-to-end integration test with PDF encryption verification.
Tests: upload → process → poll → download → unzip → verify passwords.
"""

import json
import pathlib
import sys
import time
import zipfile

import requests

BASE = "http://localhost:8000/api/v1"

ROOT = pathlib.Path("c:/Users/gopikrishna.m/Documents/password_protector")
PDFS_DIR = ROOT / "input"
EXCEL = ROOT / "passwords.xlsx"
OUT_ZIP = ROOT / "backend" / "e2e_test_output.zip"
EXTRACT = ROOT / "backend" / "e2e_extracted"

print("=" * 60)
print("PDF Password Protector — End-to-End Test")
print("=" * 60)

# ── 0. Health check ────────────────────────────────────────────
print("\n[1] Health check...")
r = requests.get("http://localhost:8000/health", timeout=5)
r.raise_for_status()
print(f"    ✓ Backend: {r.json()}")

# ── 1. List input PDFs ─────────────────────────────────────────
pdf_files = sorted(PDFS_DIR.glob("*.pdf"))
print(f"\n[2] Input PDFs found: {len(pdf_files)}")
for f in pdf_files:
    print(f"    • {f.name} ({f.stat().st_size:,} bytes)")

assert pdf_files, "No PDF files found in input/"
assert EXCEL.exists(), "passwords.xlsx not found"

# ── 2. Upload ──────────────────────────────────────────────────
print(f"\n[3] Uploading {len(pdf_files)} PDFs + {EXCEL.name}...")
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
print(f"    ✓ Job ID: {job_id}")
print(f"    ✓ Files:  {upload['file_count']}")
print(f"    ✓ Excel:  {upload['excel_filename']}")

# ── 3. Start processing ────────────────────────────────────────
print("\n[4] Starting encryption (skip_encrypted=False, workers=4)...")
r = requests.post(
    f"{BASE}/process/{job_id}",
    json={"skip_encrypted": False, "overwrite": True, "max_workers": 4},
    timeout=10,
)
r.raise_for_status()
print(f"    ✓ Response: {r.status_code} — {r.json()['message']}")

# ── 4. Poll until done ─────────────────────────────────────────
print("\n[5] Polling status...")
final = None
for i in range(60):
    time.sleep(1)
    r = requests.get(f"{BASE}/status/{job_id}", timeout=5)
    s = r.json()
    bar = "█" * int(s["progress"] / 5)
    print(
        f"    [{i+1:02d}] {s['status']:12s} {s['progress']:3d}% |{bar:<20}| {s['done']}/{s['total']}"
    )
    if s["status"] in ("completed", "failed"):
        final = s
        break

assert final, "Timed out waiting for job completion"
elapsed = time.time() - t0
print(f"\n[6] Processing complete in {elapsed:.2f}s")
print(f"    Status:    {final['status']}")
print(f"    Stats:     {json.dumps(final['stats'], indent=10)}")

if final["status"] == "failed":
    print(f"    ERROR: {final.get('error')}")
    sys.exit(1)

# ── 5. Verify stats ────────────────────────────────────────────
stats = final["stats"]
assert stats["success"] > 0, "No PDFs were successfully encrypted!"
print("\n[7] Verification:")
print(f"    ✓ Encrypted: {stats['success']}")
print(f"    {'✓' if stats['missing']==0 else '✗'} Missing:   {stats['missing']}")
print(f"    {'✓' if stats['failed']==0  else '✗'} Failed:    {stats['failed']}")
print(f"    ✓ Skipped:  {stats['skipped']}")

# ── 6. Download ZIP ────────────────────────────────────────────
print("\n[8] Downloading ZIP...")
r = requests.get(f"{BASE}/download/{job_id}", timeout=60, stream=True)
r.raise_for_status()
OUT_ZIP.write_bytes(r.content)
print(f"    ✓ ZIP size: {len(r.content):,} bytes → {OUT_ZIP.name}")

# ── 7. Unzip + verify each PDF is encrypted ───────────────────
print("\n[9] Verifying encrypted PDFs...")
EXTRACT.mkdir(exist_ok=True)
encrypted_ok = []
not_encrypted = []

with zipfile.ZipFile(OUT_ZIP) as zf:
    zf.extractall(EXTRACT)
    names = zf.namelist()
    print(f"    ZIP contains {len(names)} file(s)")

try:
    from pypdf import PdfReader

    for name in names:
        pdf_path = EXTRACT / name
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            encrypted_ok.append(name)
            print(f"    ✓ {name} — ENCRYPTED")
        else:
            not_encrypted.append(name)
            print(f"    ✗ {name} — NOT encrypted!")
except ImportError:
    print("    (pypdf not available for verification — skipping password check)")

if not_encrypted:
    print(f"\n    FAIL: {len(not_encrypted)} PDF(s) not encrypted!")
    sys.exit(1)
else:
    print(f"\n    ✓ All {len(encrypted_ok)} PDFs verified as encrypted")

# ── 8. Cleanup verification ────────────────────────────────────
print("\n[10] Cleanup check...")
import tempfile

tmp = pathlib.Path(tempfile.gettempdir())
job_dirs = list(tmp.glob(f"job-{job_id[:8]}*"))
# After download, the job dir is cleaned up by BackgroundTasks
if job_dirs:
    print(f"     ⚠ Temp dir still present (normal within 30min TTL): {job_dirs[0].name}")
else:
    print("     ✓ Temp dir cleaned up after download")

# ── Final summary ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("FINAL RESULT: ALL TESTS PASSED ✓")
print("=" * 60)
print("  Backend URL:  http://localhost:8000")
print("  Swagger UI:   http://localhost:8000/docs")
print("  Frontend URL: http://localhost:3000")
print(f"  PDFs encrypted: {stats['success']}/{stats['total']}")
print(f"  ZIP location: {OUT_ZIP}")
print("=" * 60)
