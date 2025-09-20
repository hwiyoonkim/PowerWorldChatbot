import json
import argparse

def parse_aux(aux_path):
    lines = []
    with open(aux_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            l = line.strip()
            if l and not l.startswith("//"):
                lines.append(l)
    return lines

def make_dataset(aux_path, output_path):
    lines = parse_aux(aux_path)
    # example: count buses, generators etc from lines (you will customize this)
    # Here we make simple synthetic questions
    ds = []
    ds.append({
        "instruction": "Summarize the power system case.",
        "input": "\n".join(lines[:50]),
        "output": "Summary: ..."  # you should generate or write this
    })
    # add more entries as desired

    with open(output_path, "w", encoding="utf-8") as f:
        for entry in ds:
            json.dump(entry, f)
            f.write("\\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aux", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    make_dataset(args.aux, args.out)
