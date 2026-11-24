fp = r"C:\Users\Anand\AppData\Local\Temp\report_now.txt"
lines = open(fp, encoding="utf-8").readlines()
for i, l in enumerate(lines):
    if "parikh" in l.lower() or "jolly" in l.lower() or "assistant professor" in l.lower() or "associate professor" in l.lower():
        print(f"Line {i+1}: {l.strip()}")
