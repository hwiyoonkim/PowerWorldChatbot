from flask import Flask, request, jsonify, render_template
from win32com.client import Dispatch
import pythoncom
import os
import traceback
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
EXPORT_FOLDER = "exports"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

case_path = {"pwb": None}
pw = None
kb_text = ""

# Load LLaMA 2 13B model
model_name = "meta-llama/Llama-2-13b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name, torch_dtype=torch.float16, device_map="auto"
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    pythoncom.CoInitialize()
    global pw, case_path, kb_text

    uploaded_files = request.files.getlist("file")
    case_path["pwb"] = None

    for file in uploaded_files:
        filename = file.filename
        if filename.endswith(".pwb"):
            path = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
            file.save(path)
            case_path["pwb"] = path

    if not case_path["pwb"]:
        return jsonify({"error": "Please upload a .pwb file."}), 400

    try:
        print(f"Trying to open: {case_path['pwb']}")
        pw = Dispatch("pwrworld.SimulatorAuto")
        print("PowerWorld COM object initialized.")

        result = pw.OpenCase(case_path["pwb"])
        print("OpenCase result:", result)

        # === Export AUX file ===
        aux_path = os.path.abspath(os.path.join(EXPORT_FOLDER, "full_case_export.aux"))
        print("Exporting case to AUX:", aux_path)
        pw.SaveCase(aux_path, "AUX")
        print("AUX export complete.")

        # === Build knowledge base from AUX (or live data) ===
        kb_text = build_knowledge_base(pw)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to open or convert case: {str(e)}"}), 500

    return jsonify({"message": "PowerWorld case opened and knowledge base created."})

@app.route("/ask", methods=["POST"])
def ask_question():
    global pw, kb_text
    pythoncom.CoInitialize()

    data = request.get_json()
    query = data.get("query", "").strip()

    if not pw or not kb_text:
        return jsonify({"error": "PowerWorld case not loaded."}), 400

    try:
        prompt = (
            f"<s>[INST] <<SYS>>\n"
            f"You are a helpful assistant that answers questions about PowerWorld case summaries.\n"
            f"<</SYS>>\n\n"
            f"Context:\n{kb_text}\n\n"
            f"User Question: {query} [/INST]"
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        output = model.generate(**inputs, max_new_tokens=200)
        answer = tokenizer.decode(output[0], skip_special_tokens=True)
        final_answer = answer.split("[/INST]")[-1].strip()

        return jsonify({"answer": final_answer})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Error answering question: {str(e)}"}), 500

def build_knowledge_base(pw):
    print("Building knowledge base...")
    kb_lines = []

    try:
        for objtype, field in [
            ("bus", "BusNum"),
            ("branch", "LineCircuit"),
            ("gen", "GenID"),
            ("load", "LoadID")
        ]:
            _, data = pw.GetParametersMultipleElement(objtype, [field], [""])
            count = len(data)
            kb_lines.append(f"There are {count} {objtype}s in the system.")

        _, bus_data = pw.GetParametersMultipleElement("bus", ["BusNum", "BusName", "NomKV"], [""])
        for entry in bus_data:
            try:
                num, name, kv = entry
                kb_lines.append(f"Bus {name} (#{num}) operates at {kv} kV.")
            except:
                continue

    except Exception as e:
        print("Error in build_knowledge_base:", e)

    return "\n".join(kb_lines)

if __name__ == "__main__":
    app.run(debug=True)
