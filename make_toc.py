import json, re, sys

lines = open(r"C:\Users\Anand\AppData\Local\Temp\report_now.txt", encoding="utf-8").read().splitlines()

entries = [
    ("Candidate's Declaration", 0),
    ("Certificate", 0),
    ("Acknowledgement", 0),
    ("Abstract", 0),
    ("List of Tables", 0),
    ("List of Figures", 0),
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
        level = 2 if re.match(r"^\d+\.\d+\.\d+", s) else 1
        entries.append((s, level))

print("entries:", len(entries))

def build(pages):
    rows = []
    for (title, level), page in zip(entries, pages):
        if level == 0:
            pad, weight, size = "0", "bold", "11pt"
        elif level == 1:
            pad, weight, size = "14pt", "normal", "10.5pt"
        else:
            pad, weight, size = "28pt", "normal", "10.5pt"
        rows.append(
            f'<tr>'
            f'<td style="border:none;padding:0;margin:0;width:88%;">'
            f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
            f'font-weight:{weight};text-align:left;padding-left:{pad};">{title}</p></td>'
            f'<td style="border:none;padding:0;margin:0;width:12%;">'
            f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
            f'text-align:right;">{page}</p></td></tr>'
        )
    return '<table style="border-collapse:collapse;width:100%;border:none;">' + "".join(rows) + '</table>'

pages = ["00"] * len(entries)
html = build(pages)
json.dump({"html": html, "count": len(entries), "titles": [e[0] for e in entries]},
          open("toc_draft.json", "w", encoding="utf-8"))
print("draft html len", len(html))
