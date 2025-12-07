import json
from collections import OrderedDict

INPUT_FILE = "dataset.jsonl"
OUTPUT_FILE = "cleaned_dataset.jsonl"

def normalize_output(text):
    return (
        text.replace("buss", "buses")
            .replace("gens", "generators")
            .replace("branchs", "branches")
            .replace("case contains", "This case contains")
            .replace("Case contains", "This case contains")
    )

def main():
    seen_instructions = OrderedDict()
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                instr = item["instruction"].strip()
                output = normalize_output(item["output"].strip())

                # Skip if already seen
                if instr in seen_instructions:
                    continue

                # Optional: filter out zero-output examples
                if "0 buses" in output and "0 generators" in output:
                    continue

                seen_instructions[instr] = {
                    "instruction": instr,
                    "input": "",
                    "output": output
                }

            except json.JSONDecodeError:
                continue

    # Write cleaned version
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in seen_instructions.values():
            json.dump(item, f)
            f.write("\n")

    print(f" Cleaned dataset written to {OUTPUT_FILE}")
    print(f" Total examples: {len(seen_instructions)}")

if __name__ == "__main__":
    main()
