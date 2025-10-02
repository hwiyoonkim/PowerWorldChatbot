import sqlite3
import json
import argparse

def make_dataset_from_db(db_path, out_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    ds = []

    cur.execute("SELECT COUNT(*) FROM Bus")
    n_bus = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Gen")
    n_gen = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Load")
    n_load = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Branch")
    n_branch = cur.fetchone()[0]

    summary = (
        f"The case contains {n_bus} buses, {n_gen} generators, "
        f"{n_load} loads, and {n_branch} transmission branches."
    )

    ds.append({
        "instruction": "Summarize the power system case.",
        "input": "",
        "output": summary
    })

    with open(out_path, "w", encoding="utf-8") as f:
        for item in ds:
            json.dump(item, f)
            f.write("\n")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    make_dataset_from_db(args.db, args.out)