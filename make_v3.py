import json, re
entries = json.load(open(r"C:\Users\Anand\AppData\Local\Temp\toc_entries.json", encoding="utf-8"))
rows = []
for title, level, page in entries:
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
json.dump({"html": html, "count": len(entries)}, open("toc_v3.json", "w", encoding="utf-8"))
print("rows", len(entries), "len", len(html))
