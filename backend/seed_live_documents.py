import os
import requests

BASE_URL = "http://127.0.0.1:8001/api"
SAMPLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "sample_invoices"))

files_to_upload = [
    "INV-2026-001.pdf",
    "NOS-26-27-0418.pdf",
    "STAT-2026-904.pdf",
    "MTS-SALES-2026-088.pdf"
]

def seed_invoices():
    print(f"Uploading invoices from {SAMPLE_DIR}...")
    for filename in files_to_upload:
        filepath = os.path.join(SAMPLE_DIR, filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        with open(filepath, "rb") as f:
            resp = requests.post(f"{BASE_URL}/documents/upload", files={"file": (filename, f, "application/pdf")})
        
        if resp.status_code == 200:
            doc_data = resp.json()
            doc_id = doc_data["document_id"]
            print(f"Uploaded {filename} -> ID: {doc_id}")
            # Process document
            proc_resp = requests.post(f"{BASE_URL}/documents/{doc_id}/process")
            if proc_resp.status_code == 200:
                print(f"Processed {filename} -> Status: {proc_resp.json()['status']}")
            else:
                print(f"Processing failed for {filename}: {proc_resp.text}")
        else:
            print(f"Upload failed for {filename}: {resp.text}")

    # Now let's post one of them to GL to show active posted ledger and trial balance!
    docs = requests.get(f"{BASE_URL}/documents").json()
    for d in docs:
        if d["status"] in ("PROCESSED", "REVIEW_REQUIRED"):
            detail = requests.get(f"{BASE_URL}/documents/{d['id']}").json()
            if detail.get("proposal"):
                post_res = requests.post(f"{BASE_URL}/journal/post", json=detail["proposal"])
                if post_res.status_code == 200:
                    print(f"Posted {detail.get('invoice', {}).get('invoice_number', d['filename'])} to General Ledger!")

if __name__ == "__main__":
    seed_invoices()
