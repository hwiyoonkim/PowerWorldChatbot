import os
import sqlite3
import traceback
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from win32com.client import Dispatch
import pythoncom

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    # ✅ COM init for this Flask thread
    pythoncom.CoInitialize()

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    pwb_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(pwb_path)

    print(f"Trying to open case: {pwb_path}")
    print(f"File exists: {os.path.exists(pwb_path)}")

    try:
        # Dispatch PowerWorld SimAuto
        pw = Dispatch("pwrworld.SimulatorAuto")

        # Correct COM call
        result = pw.OpenCase(pwb_path)
        print("OpenCase result:", result)

        return jsonify({"message": f"Successfully opened case: {filename}"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f"Failed to open or convert case: {e}"}), 500

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question", "")
    return jsonify({"answer": f"Sorry, answering questions is not implemented yet. You asked: {question}"})


if __name__ == '__main__':
    app.run(debug=True)
