import json

rows = [
    ("Candidate’s Declaration", "2", 0),
    ("Certificate", "3", 0),
    ("Acknowledgement", "4", 0),
    ("Abstract", "5", 0),
    ("List of Tables", "8", 0),
    ("List of Figures", "9", 0),
    ("List of Symbols and Abbreviations", "10", 0),
    ("CHAPTER 1: INTRODUCTION", "12", 0),
    ("1.1 Background and Problem Domain", "12", 1),
    ("1.2 The Industrial Problem: Manual Accounting Bottlenecks", "12", 1),
    ("1.3 The Semantic & Accounting Chasm in Modern Document AI", "13", 1),
    ("1.4 Problem Statement", "13", 1),
    ("1.5 Objectives of the Project", "14", 1),
    ("1.6 Scope of Work and Key Technical Deliverables", "14", 1),
    ("1.7 Alignment with Sustainable Development Goals (SDGs)", "15", 1),
    ("1.8 Organization of the Report", "15", 1),
    ("CHAPTER 2: LITERATURE SURVEY", "17", 0),
    ("2.1 Evolution of Document Intelligence & Information Extraction", "17", 1),
    ("2.2 Base Paper 1 Review: SmolVLM and Heuristics (Rana et al., 2025)", "17", 1),
    ("2.3 Base Paper 2 Review: Table Layout Correction (Yao et al., 2026)", "18", 1),
    ("2.4 Multimodal Transformers and Benchmark Datasets", "18", 1),
    ("2.5 Industry Landscape & Commercial Tools Analysis", "19", 1),
    ("2.6 Comparative Analysis of Existing Approaches", "19", 1),
    ("2.7 Identified Research Gaps and Novelties", "20", 1),
    ("CHAPTER 3: METHODOLOGY AND SYSTEM ARCHITECTURE", "21", 0),
    ("3.1 Proposed End-to-End System Pipeline", "21", 1),
    ("3.2 Stage 1 & 2: Ingestion and Layout-Preserving Markdown", "21", 1),
    ("3.3 Stage 3: Table Layout Correction & Semantic Decoupling", "21", 1),
    ("3.4 Stage 4: Template-Free Heuristic Field Extraction", "21", 1),
    ("3.5 Stage 5: Accounting Interpretation Engine", "22", 1),
    ("3.5.1 Capitalization Policy (AS 10 / Ind AS 16)", "22", 2),
    ("3.5.2 Statutory GST Classification & Place of Supply (POS)", "22", 2),
    ("3.5.3 Input Tax Credit (ITC) & Section 17(5) Blocked Credits", "22", 2),
    ("3.5.4 Double-Entry Journal Proposal Generation", "23", 2),
    ("3.6 Stage 6: Deterministic Multi-Stage Invariant Validation Suite", "23", 1),
    ("3.7 Stage 7: Ledger Posting & Final Accounts Generation", "24", 1),
    ("3.8 Human-in-the-Loop Review Panel and Immutable Audit Logging", "24", 1),
    ("CHAPTER 4: IMPLEMENTATION DETAILS", "25", 0),
    ("4.1 Technology Stack & Architectural Rationale", "25", 1),
    ("4.2 Relational Database Design & Schema Specifications", "25", 1),
    ("4.3 Algorithmic Formulation & Zero-Float Decimal Computing", "26", 1),
    ("4.4 Rule-Based Semantic Mapping & HSN Prefix Matching", "26", 1),
    ("4.5 Backend Architecture & RESTful API Specifications", "27", 1),
    ("4.6 Frontend Architecture & Verification Interface", "27", 1),
    ("CHAPTER 5: RESULTS AND PERFORMANCE ANALYSIS", "28", 0),
    ("5.1 Dataset Description and Evaluation Protocols", "28", 1),
    ("5.2 Experimental Setup & Comparative Ablation Studies (E1 - E6)", "28", 1),
    ("5.3 Document Extraction & Table Parsing Evaluation (TEDS Metric)", "29", 1),
    ("5.4 Invariant Verification Pass Rates and Arithmetic Reliability", "29", 1),
    ("5.5 Step-by-Step Test Scenarios Walkthrough", "29", 1),
    ("5.5.1 Scenario 1: Mixed Asset/Expense Invoice (INV-2026-001)", "29", 2),
    ("5.5.2 Scenario 2: Inter-State Cloud Hosting with IGST (INV-2026-002)", "29", 2),
    ("5.5.3 Scenario 3: Consumables with Trade Discount (INV-2026-003)", "30", 2),
    ("5.5.4 Scenario 4: Complex Multi-Slab GST Tax Invoice (NOS-26-27-0418)", "30", 2),
    ("5.6 Automated Test Suite Execution & Code Coverage (35 Tests Passing)", "30", 1),
    ("5.7 Generated Financial Statements Analysis", "31", 1),
    ("CHAPTER 6: ADVANCED SYSTEM FEATURES AND ENTERPRISE ARCHITECTURE EXTENSIONS", "33", 0),
    ("6.1 Overview of Enterprise Accounting and System Extensions", "33", 1),
    ("6.2 Statutory Day Books and Advanced Domain Accounting Subsystems", "34", 1),
    ("6.3 Operational Resilience, Security, Optical Fallback, and ERP Integration", "37", 1),
    ("6.4 Comprehensive System Capabilities and Architectural Specifications", "40", 1),
    ("6.5 End-to-End System Execution Flow and Formal Balance Invariants", "44", 1),
    ("6.6 System Verification Suite and Empirical Performance Benchmarks", "46", 1),
    ("6.7 Industrial Viability and Enterprise Deployment Synthesis", "48", 1),
    ("CHAPTER 7: CONCLUSION AND FUTURE SCOPE", "49", 0),
    ("7.1 Summary of Contributions", "49", 1),
    ("7.2 Industry Viability and Unique Selling Propositions (USPs)", "49", 1),
    ("7.3 System Limitations", "50", 1),
    ("7.4 Roadmap for 8th Semester Major Project", "50", 1),
    ("REFERENCES", "51", 0),
]

print("rows:", len(rows))

html_rows = []
for title, page, level in rows:
    if level == 0:
        style = "font-weight:bold; padding:1.2pt 0;"
    elif level == 1:
        style = "padding-left:14pt; padding:0.8pt 0 0.8pt 14pt;"
    else:
        style = "padding-left:28pt; padding:0.6pt 0 0.6pt 28pt;"
    html_rows.append(
        f'<tr><td style="{style} font-family:\'Times New Roman\',serif; font-size:10.5pt; text-align:left;">{title}</td>'
        f'<td style="font-family:\'Times New Roman\',serif; font-size:10.5pt; text-align:right; width:52pt; padding:0.8pt 0;">{page}</td></tr>'
    )

html = (
    '<table style="border-collapse:collapse; width:100%; border:none;">'
    + "".join(html_rows)
    + "</table>"
)

with open("toc.html", "w", encoding="utf-8") as f:
    f.write(html)

with open("toc.json", "w", encoding="utf-8") as f:
    json.dump({"html": html, "count": len(rows)}, f)

print("written toc.json")
