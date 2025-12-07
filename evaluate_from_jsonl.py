import requests
import json
import csv
import time
import difflib

INPUT_FILE = "cleaned_dataset.jsonl"
OUTPUT_CSV = "eval_from_jsonl.csv"
FLASK_URL = "http://localhost:5000/ask"  # make sure your Flask app is running

def f1_score(pred, gold):
    pred_tokens = pred.lower().split()
    gold_tokens = gold.lower().split()
    common = set(pred_tokens) & set(gold_tokens)
    precision = len(common) / len(pred_tokens) if pred_tokens else 0
    recall = len(common) / len(gold_tokens) if gold_tokens else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)

def hallucinated(pred, gold):
    similarity = difflib.SequenceMatcher(None, pred.lower(), gold.lower()).ratio()
    return similarity < 0.5 and pred.lower() != gold.lower()

def query_flask(instruction):
    start = time.time()
    try:
        response = requests.post(FLASK_URL, json={"question": instruction})
        answer = response.json().get("answer", "").strip()
    except Exception as e:
        answer = f"[Error] {e}"
    end = time.time()
    return answer, round(end - start, 3)

results = []

with open(INPUT_FILE, 'r') as f:
    for i, line in enumerate(f, 1):
        try:
            item = json.loads(line)
            instruction = item.get("instruction", "").strip()
            expected = item.get("output", "").strip()
            
            print(f"[{i}] Asking: {instruction}")
            predicted, latency = query_flask(instruction)

            em = predicted.lower() == expected.lower()
            f1 = round(f1_score(predicted, expected), 2)
            halluc = hallucinated(predicted, expected)

            print(f"   Expected: {expected}")
            print(f"   Predicted: {predicted}")
            print(f"   EM: {em} | F1: {f1} | Hallucinated: {halluc} | {latency}s")

            results.append({
                "Instruction": instruction,
                "Expected": expected,
                "Predicted": predicted,
                "Exact Match": em,
                "F1 Score": f1,
                "Hallucinated": halluc,
                "Latency (s)": latency
            })

        except Exception as e:
            print(f"Error on line {i}: {e}")

# Write results to CSV
with open(OUTPUT_CSV, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

# Summary
total = len(results)
em_total = sum(1 for r in results if r["Exact Match"])
f1_avg = sum(r["F1 Score"] for r in results) / total
halluc_total = sum(1 for r in results if r["Hallucinated"])

print("\n Evaluation Summary")
print(f" Exact Match Accuracy: {em_total}/{total} = {em_total / total:.2f}")
print(f" Average F1 Score: {f1_avg:.2f}")
print(f" Hallucination Rate: {halluc_total}/{total} = {halluc_total / total:.2f}")
print(f" Results saved to: {OUTPUT_CSV}")
