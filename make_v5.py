import json

entries = json.load(open(r'C:\Users\Anand\AppData\Local\Temp\toc_entries4.json', encoding='utf-8'))

rows = []
for e in entries:
    title, level, page = e['title'], e['level'], e['page']
    if level == 0:
        pad, weight, size = '0', 'bold', '11pt'
    elif level == 1:
        pad, weight, size = '14pt', 'normal', '10.5pt'
    else:
        pad, weight, size = '28pt', 'normal', '10.5pt'
    rows.append(
        '<tr>'
        f'<td style="border:none;padding:0;margin:0;width:88%;">'
        f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
        f'font-weight:{weight};text-align:left;padding-left:{pad};">{title}</p></td>'
        '<td style="border:none;padding:0;margin:0;width:12%;">'
        f'<p style="margin:0;padding:0;line-height:1.15;font-family:Times New Roman,serif;font-size:{size};'
        f'text-align:right;">{page}</p></td></tr>'
    )

html = '<table style="border-collapse:collapse;width:100%;border:none;">' + ''.join(rows) + '</table>'
json.dump({'html': html, 'count': len(entries)}, open(r'C:\Users\Anand\projects\Minor Project\toc_v5.json', 'w', encoding='utf-8'))
print('toc rows', len(entries), 'len', len(html))

tables = [
    ('2.1', 'Comparative Analysis of Document AI Frameworks & Invoice Systems', 19),
    ('2.2', 'Evaluation of Commercial AP Automation Tools against Proposed Framework', 20),
    ('4.1', 'Technology Stack Components and Engineering Specifications', 25),
    ('6.1', 'Full-Spectrum System Capabilities and Technical Architecture', 40),
    ('6.2', 'Unified System Codebase Metrics and Architectural Dimensions', 43),
    ('6.3', 'Empirical Benchmark and Latency Profile across Pipelines', 47),
]
figures = [
    ('1.1', 'End-to-End System Architecture: Document Intelligence to Verified Financial Books', 16),
    ('2.1', 'Table Layout Correction and Summary Trapping Mechanism (Yao et al. Adaptation)', 20),
    ('3.1', 'Accounting Interpretation, Capitalization Policy, and Statutory GST Decision Flowchart', 23),
    ('4.1', 'Relational Database Entity-Relationship (ER) Schema for the Accounting Platform', 26),
    ('5.1', 'Comparative Performance Across Experimental Ablation Configurations (E1 to E6)', 28),
    ('5.2', 'Automated Pytest Execution Distribution Across 35 Unit and Invariant Test Cases', 30),
]


def grid(rows, head0):
    W = ['14%', '74%', '12%']

    def cell(c, i, extra=''):
        return (f'<td style="width:{W[i]};border:1px solid #cccccc;padding:4pt 6pt;{extra}">'
                f'<p style="margin:0;font-family:Times New Roman,serif;font-size:10.5pt;">{c}</p></td>')

    head = ''.join(cell(h, i, 'font-weight:bold;background-color:#f2f2f2;')
                   for i, h in enumerate([head0, 'Title', 'Page']))
    body = ''.join(
        '<tr>' + cell(n, 0) + cell(t, 1) + cell(str(p), 2, 'text-align:right;') + '</tr>'
        for n, t, p in rows)
    return ('<table style="border-collapse:collapse;width:100%;table-layout:fixed;">'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>')


json.dump({'html': grid(tables, 'Table No.')}, open(r'C:\Users\Anand\projects\Minor Project\lot_v5.json', 'w', encoding='utf-8'))
json.dump({'html': grid(figures, 'Figure No.')}, open(r'C:\Users\Anand\projects\Minor Project\lof_v5.json', 'w', encoding='utf-8'))
print('lists written')
