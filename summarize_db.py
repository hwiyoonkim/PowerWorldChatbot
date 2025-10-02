import sqlite3
import os

def summarize_db(db_path):
    if not os.path.exists(db_path):
        return "[Missing database]", "[No summary generated.]"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    raw_summary = []
    explanation = []

    def safe_query(query):
        try:
            cursor.execute(query)
            return cursor.fetchall()
        except:
            return []

    # --- Basic Table Summaries ---
    tables = ["Bus", "Branch", "Generator", "Load", "CaseInformation"]
    for table in tables:
        rows = safe_query(f"SELECT COUNT(*) FROM '{table}'")
        count = rows[0][0] if rows else 0
        raw_summary.append(f"{table}: {count} rows")

    # --- Explanation ---
    bus_count = safe_query("SELECT COUNT(*) FROM Bus")
    load_count = safe_query("SELECT COUNT(*) FROM Load")
    gen_count = safe_query("SELECT COUNT(*) FROM Generator")
    branch_count = safe_query("SELECT COUNT(*) FROM Branch")

    explanation.append("This PowerWorld case includes:")
    if bus_count: explanation.append(f"- {bus_count[0][0]} buses")
    if gen_count: explanation.append(f"- {gen_count[0][0]} generators")
    if load_count: explanation.append(f"- {load_count[0][0]} loads")
    if branch_count: explanation.append(f"- {branch_count[0][0]} branches")

    # --- Try to extract case name and date ---
    case_info = safe_query("SELECT * FROM CaseInformation")
    if case_info and len(case_info[0]) >= 2:
        explanation.append(f"- Case description: {case_info[0][0]}")
        explanation.append(f"- File created: {case_info[0][1]}")

    conn.close()

    return {
        "raw": "\n".join(raw_summary)
    }, "\n".join(explanation)
