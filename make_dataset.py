import sqlite3
import json
import random
import os

# ----------------------
# Config
# ----------------------
DB_PATH = "caseinfo.db"
OUT_FILE = "dataset.jsonl"
NUM_EXAMPLES = 1000

# ----------------------
# Utility functions
# ----------------------
def get_counts():
    """Fetch counts for each table from the PowerWorld SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    counts = {}
    for table in ["Bus", "Gen", "Load", "Branch"]:
        try:
            c.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = c.fetchone()[0]
        except Exception:
            counts[table] = 0
    conn.close()

    print(" Counts from DB:", counts)
    return counts


def get_sample_buses(n=5):
    """Fetch sample bus info (BusNum, BusName, NomKV)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT "BusNum","BusName","NomKV" FROM "Bus" LIMIT ?', (n,))
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


def get_sample_gens(n=5):
    """Fetch sample generator info (BusNum, GenID, GenMW, Status)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT "BusNum","GenID","GenMW","Status" FROM "Gen" LIMIT ?', (n,))
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()
    return rows


# ----------------------
# Dataset generation
# ----------------------
def generate_examples():
    counts = get_counts()
    buses = get_sample_buses(10)
    gens = get_sample_gens(10)

    qas = []

    # --- Summary style questions ---
    summary_phrases = [
        "Can you summarize the case?",
        "Give me an overview of this system.",
        "What does this case contain?",
        "Provide a short summary of the network.",
        "Summarize the case in terms of buses, gens, loads, branches."
    ]
    summary_output = (
        f"This case contains {counts.get('Bus', 0)} buses, "
        f"{counts.get('Gen', 0)} generators, "
        f"{counts.get('Load', 0)} loads, and "
        f"{counts.get('Branch', 0)} branches."
    )
    for q in summary_phrases:
        qas.append({
            "instruction": q,
            "input": "",
            "output": summary_output
        })

    # --- Count questions ---
    count_templates = [
        ("Bus", ["How many buses are there?", "Number of buses?", "Count of buses?", "Total buses in the system?"]),
        ("Gen", ["How many generators are in the system?", "Number of generators?", "Count of generators?", "Total generators?"]),
        ("Load", ["How many loads does the case have?", "Number of loads?", "Count of loads?", "Total loads?"]),
        ("Branch", ["How many branches are there?", "Number of lines?", "Count of branches?", "Total transmission lines?"])
    ]

    for table, qs in count_templates:
        plural_name = {
            "Bus": "buses",
            "Gen": "generators",
            "Load": "loads",
            "Branch": "branches"
        }[table]

        for q in qs:
            qas.append({
                "instruction": q,
                "input": "",
                "output": f"There are {counts.get(table, 0)} {plural_name} in this case."
            })

    # --- Bus KV questions ---
    for busnum, busname, kv in buses:
        kv_qs = [
            f"What is the nominal voltage of bus {busnum}?",
            f"At what kV does {busname} operate?",
            f"Bus {busnum} nominal kV?",
            f"Voltage rating of {busname}?"
        ]
        for q in kv_qs:
            qas.append({
                "instruction": q,
                "input": "",
                "output": f"Bus {busnum} ({busname}) operates at {kv} kV."
            })

    # --- Generator MW questions ---
    for busnum, genid, mw, status in gens:
        gen_qs = [
            f"What is the MW output of generator {genid} at bus {busnum}?",
            f"How much power does generator {genid} produce?",
            f"Generator {genid} at bus {busnum}, what is its MW?",
            f"Status and MW of generator {genid}?"
        ]
        for q in gen_qs:
            qas.append({
                "instruction": q,
                "input": "",
                "output": f"Generator {genid} at bus {busnum} produces {mw} MW. Status: {status}."
            })

    # --- Random paraphrased variations ---
    more_qas = []
    all_templates = list(qas)
    while len(more_qas) + len(qas) < NUM_EXAMPLES:
        ex = random.choice(all_templates)
        var_q = ex["instruction"].rstrip("?").capitalize() + " please?"
        more_qas.append({
            "instruction": var_q,
            "input": ex["input"],
            "output": ex["output"]
        })

    dataset = qas + more_qas[: NUM_EXAMPLES - len(qas)]

    # --- Save to file ---
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for ex in dataset:
            json.dump(ex, f, ensure_ascii=False)
            f.write("\n")

    print(f"\n Dataset saved to {OUT_FILE} with {len(dataset)} examples")
    print(" Example preview:")
    for ex in dataset[:5]:
        print(f"  Q: {ex['instruction']}")
        print(f"  A: {ex['output']}\n")

    return dataset


# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f" Database not found: {DB_PATH}")
        print("  Please upload a .pwb file first to populate the database.")
    else:
        generate_examples()
