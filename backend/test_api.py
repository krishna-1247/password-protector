"""End-to-end API integration test."""

import json
import pathlib
import time

import requests

BASE = "http://localhost:8000/api/v1"

# 1. Upload
pdfs_dir = pathlib.Path("../input")
pdf_files = list(pdfs_dir.glob("*.pdf"))
excel = pathlib.Path("../passwords.xlsx")

files = [("pdfs", (f.name, open(f, "rb"), "application/pdf")) for f in pdf_files]
files.append(
    (
        "excel",
        (
            excel.name,
            open(excel, "rb"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    )
)

r = requests.post(f"{BASE}/upload", files=files)
r.raise_for_status()
upload = r.json()
job_id = upload["job_id"]
print("Upload OK:", json.dumps(upload, indent=2))

# 2. Process
r = requests.post(
    f"{BASE}/process/{job_id}",
    json={"skip_encrypted": False, "overwrite": True, "max_workers": 2},
)
r.raise_for_status()
print("Process started:", r.json())

# 3. Poll until done
final = None
for i in range(30):
    time.sleep(1)
    r = requests.get(f"{BASE}/status/{job_id}")
    s = r.json()
    pct = s["progress"]
    status = s["status"]
    print(f"  [{i+1:02d}] status={status} progress={pct}%  done={s['done']}/{s['total']}")
    if status in ("completed", "failed"):
        final = s
        break

if final:
    print("\nFinal stats:")
    print(json.dumps(final["stats"], indent=2))

    # 4. Download
    if final["status"] == "completed":
        r = requests.get(f"{BASE}/download/{job_id}")
        r.raise_for_status()
        out = pathlib.Path("test_output.zip")
        out.write_bytes(r.content)
        print(f"\nDownloaded ZIP: {len(r.content):,} bytes -> {out}")
    else:
        print("Job failed:", final.get("error"))
else:
    print("Timed out waiting for job")
