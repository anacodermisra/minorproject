import json, re

pages = [2, 3, 4, 5, 9, 11, 12,          # front matter
         14, 14, 14, 15, 15, 16, 16, 17, 17,
         19, 19, 19, 20, 20, 21, 21, 22,
         23, 23, 23, 23, 23, 24, 24, 24, 24, 25, 25, 26, 26,
         27, 27, 27, 28, 28, 29, 29,
         30, 30, 30, 31, 31, 31, 31, 31, 32, 32, 32, 33,
         35, 35, 36, 39, 42, 46, 48, 50,
         51, 51, 51, 52, 52,
         53]

draft = json.load(open("toc_draft.json", encoding="utf-8"))
titles_count = draft["count"]
assert len(pages) == titles_count, (len(pages), titles_count)

def build():
    rows = []
    for (title, level), page in zip(draft_titles, pages):
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

# rebuild entries with levels from make_toc logic
import io
src = open("make_toc.py", encoding="utf-8").read()
ns = {}
exec(src.split("def build(")[0], ns)
draft_titles = ns["entries"]
assert len(draft_titles) == titles_count

html = build()
json.dump({"html": html, "count": len(draft_titles)}, open("toc_final.json", "w", encoding="utf-8"))
print("final rows", len(draft_titles), "len", len(html))
