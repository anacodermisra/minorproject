import json, re

# Reuse the rows list by executing build_toc.py's data section indirectly
src = open("build_toc.py", encoding="utf-8").read()
start = src.index("rows = [")
end = src.index("print(\"rows:")
ns = {}
exec(src[start:end], ns)
rows = ns["rows"]

html_rows = []
for title, page, level in rows:
    if level == 0:
        pad = "0"
        weight = "bold"
    elif level == 1:
        pad = "14pt"
        weight = "normal"
    else:
        pad = "28pt"
        weight = "normal"

    html_rows.append(
        f'<tr>'
        f'<td style="border:none; padding:0; margin:0;">'
        f'<p style="margin:0; padding:0; line-height:1.0; font-family:\'Times New Roman\',serif; font-size:10.5pt; font-weight:{weight}; text-align:left; padding-left:{pad};">{title}</p>'
        f'</td>'
        f'<td style="border:none; padding:0; margin:0; width:44pt;">'
        f'<p style="margin:0; padding:0; line-height:1.0; font-family:\'Times New Roman\',serif; font-size:10.5pt; text-align:right;">{page}</p>'
        f'</td>'
        f'</tr>'
    )

html = '<table style="border-collapse:collapse; width:100%; border:none;">' + "".join(html_rows) + "</table>"

with open("toc.json", "w", encoding="utf-8") as f:
    json.dump({"html": html, "count": len(rows)}, f)

print("rows", len(rows), "len", len(html))
