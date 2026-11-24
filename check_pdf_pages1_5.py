import pymupdf

doc = pymupdf.open(r"C:\Users\Anand\AppData\Local\Temp\report_v5.pdf")
for pno in range(5):
    print(f"=== Page {pno+1} ===")
    t = doc[pno].get_text()
    print(t.encode("ascii", errors="replace").decode("ascii"))
