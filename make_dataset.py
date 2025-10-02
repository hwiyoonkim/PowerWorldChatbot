import sqlite3
import json
import random

DB_PATH = "caseinfo.db"
OUT_FILE = "dataset.jsonl"
NUM_EXAMPLES = 1000

# ----------------------
# Utility functions
# ----------------------
def get_counts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    counts = {}
    for table in ["Bus", "Gen", "Load", "Branch"]:
        try:
            c.execute(f'SELECT COUNT(*) FROM "{table}"')
            counts[table] = c.fetchone()[0]
        except:
            counts[table] = 0
    conn.close()
    return counts

def get_sample_buses(n=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT "BusNum","BusName","NomKV" FROM "Bus" LIMIT ?', (n,))
        rows = c.fetchall()
    except:
        rows = []
    conn.close()
    return rows

def get_sample_gens(n=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT "BusNum","GenID","GenMW","Status" FROM "Gen" LIMIT ?', (n,))
        rows = c.fetchall()
    except:
        rows = []
    conn.close()
    return rows

# ----------------------
# Generate synthetic Q&A
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
    for q in summary_phrases:
        qas.append({
            "instruction": q,
            "input": "",
            "output": f"This case contains {counts.get('Bus',0)} buses, "
                      f"{counts.get('Gen',0)} generators, "
                      f"{counts.get('Load',0)} loads, and "
                      f"{counts.get('Branch',0)} branches."
        })

    # --- Count questions ---
    count_templates = [
        ("Bus", ["How many buses are there?", "Number of buses?", "Count of buses?", "Total buses in the system?"]),
        ("Gen", ["How many generators are in the system?", "Number of gens?", "Count of generators?", "Total generators?"]),
        ("Load", ["How many loads does the case have?", "Number of loads?", "Count of loads?", "Total loads?"]),
        ("Branch", ["How many branches are there?", "Number of lines?", "Count of branches?", "Total transmission lines?"])
    ]
    for table, qs in count_templates:
        for q in qs:
            qas.append({
                "instruction": q,
                "input": "",
                "output": f"There are {counts.get(table,0)} {table.lower()}s in this case."
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

    # --- Generator questions ---
    for busnum, genid, mw, status in gens:
        gen_qs = [
            f"What is the MW output of generator {genid} at bus {busnum}?",
            f"How much power does generator {genid} produce?",
            f"Generator {genid} at bus {busnum}, what is its MW?",
        ]
        for q in gen_qs:
            qas.append({
                "instruction": q,
                "input": "",
                "output": f"Generator {genid} at bus {busnum} produces {mw} MW. Status: {status}."
            })

    # --- Random variations ---
    more_qas = []
    all_templates = [qa for qa in qas]  # seed examples
    while len(more_qas) + len(qas) < NUM_EXAMPLES:
        ex = random.choice(all_templates)
        # add slight variation
        var_q = ex["instruction"].replace("?", "").lower().capitalize() + " please?"
        more_qas.append({
            "instruction": var_q,
            "input": ex["input"],
            "output": ex["output"]
        })

    return qas + more_qas[: NUM_EXAMPLES - len(qas)]


# ----------------------
# Main
# ----------------------
if __name__ == "__main__":
    dataset = generate_examples()
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        for ex in dataset:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"✅ Dataset saved to {OUT_FILE} with {len(dataset)} examples")
