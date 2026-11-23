import json, re

lines = open(r"C:\Users\Anand\AppData\Local\Temp\report_now.txt", encoding="utf-8").read().splitlines()
entries = [
    ("Candidate's Declaration", 0), ("Certificate", 0), ("Acknowledgement", 0),
    ("Abstract", 0), ("List of Tables", 0), ("List of Figures", 0),
    ("List of Symbols and Abbreviations", 0),
]
pat_ch = re.compile(r"^(CHAPTER\s+\d|REFERENCES)\b")
pat_sec = re.compile(r"^(\d+\.\d+(\.\d+)?)\s")
start = next(i for i, l in enumerate(lines) if l.strip() == "CHAPTER 1: INTRODUCTION")
for l in lines[start:]:
    s = l.strip()
    if pat_ch.match(s):
        entries.append((s, 0))
    elif pat_sec.match(s) and len(s) < 120:
        entries.append((s, 2 if re.match(r"^\d+\.\d+\.\d+", s) else 1))

pages = [2, 3, 4, 5, 9, 11, 12,
         14, 14, 14, 15, 15, 16, 16, 17, 17,
         19, 19, 19, 20, 20, 21, 21, 22,
         23, 23, 23, 23, 23, 24, 24, 24, 24, 25, 25, 26, 26,
         27, 27, 27, 28, 28, 29, 29,
         30, 30, 30, 31, 31, 31, 31, 31, 32, 32, 32, 33,
         35, 35, 36, 39, 42, 46, 48, 50,
         51, 51, 51, 52, 52,
         53]
assert len(pages) == len(entries), (len(pages), len(entries))

rows = []
for (title, level), page in zip(entries, pages):
    if level == 0:
        pad, weight, size = "0", "bold", "11pt"
    elif level == 1:
        pad, weight, size = "14pt", "normal", "10.5pt"
    else:
        pad, weight, size = "28pt", "normal", "10.5pt"
    rows.append(
        f'<tr><td style="border:none;padding:0;margin:0;width:88%;">'
        f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
        f'font-weight:{weight};text-align:left;padding-left:{pad};">{title}</p></td>'
        f'<td style="border:none;padding:0;margin:0;width:12%;">'
        f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
        f'text-align:right;">{page}</p></td></tr>'
    )
html = '<table style="border-collapse:collapse;width:100%;border:none;">' + "".join(rows) + "</table>"
json.dump({"html": html, "count": len(entries)}, open("toc_final.json", "w", encoding="utf-8"))
print("final rows", len(entries), "len", len(html))
