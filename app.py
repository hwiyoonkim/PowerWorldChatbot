import os
import sqlite3
import traceback
import re
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from win32com.client import Dispatch
import pythoncom

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def init_db():
    """Reset the database"""
    conn = sqlite3.connect('caseinfo.db')
    c = conn.cursor()
    c.execute("PRAGMA writable_schema = 1;")
    c.execute("DELETE FROM sqlite_master WHERE type IN ('table','index','trigger');")
    c.execute("PRAGMA writable_schema = 0;")
    conn.commit()
    conn.close()


def extract_and_store_case_data(pw):
    """Extract selected stable fields and store into SQLite"""
    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()

    schema = {
        "Bus": ["BusNum", "BusName", "NomKV", "AreaNum", "ZoneNum"],
        "Gen": ["BusNum", "GenID", "GenMW", "GenMvar", "Status"],
        "Load": ["BusNum", "LoadID", "LoadMW", "LoadMvar", "Status"],
        "Branch": ["BusNum", "BusNum:1", "LineCircuit", "MW", "Mvar", "Status"],
    }

    for obj, fields in schema.items():
        try:
            print(f"Extracting {obj} with fields: {fields}")
            result, data = pw.GetParametersMultipleElement(obj, fields, "")
            if result != "":
                print(f"⚠️ Could not get {obj} data: {result}")
                continue

            # Create table
            col_defs = ", ".join([f'"{f}" TEXT' for f in fields])
            c.execute(f'CREATE TABLE IF NOT EXISTS "{obj}" ({col_defs})')

            placeholders = ", ".join(["?"] * len(fields))
            insert_sql = f'INSERT INTO "{obj}" VALUES ({placeholders})'

            for row in data:
                clean_row = row[:len(fields)]
                c.execute(insert_sql, clean_row)

        except Exception as e:
            print(f"Error extracting {obj}: {e}")
            traceback.print_exc()

    conn.commit()
    conn.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
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
        pw = Dispatch("pwrworld.SimulatorAuto")
        result = pw.OpenCase(pwb_path)
        print("OpenCase result:", result)

        init_db()
        extract_and_store_case_data(pw)

        return jsonify({"message": f"Successfully opened and stored case: {filename}"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f"Failed to open or extract case: {e}"}), 500


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get("question", "").lower()

    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()

    try:
        if "how many buses" in question:
            c.execute("SELECT COUNT(*) FROM Bus")
            count = c.fetchone()[0]
            return jsonify({"answer": f"There are {count} buses in the system."})

        if "bus" in question and "kv" in question:
            match = re.search(r'bus\s+(\d+)', question)
            if match:
                busnum = match.group(1)
                c.execute("SELECT BusName, NomKV FROM Bus WHERE BusNum=?", (busnum,))
                row = c.fetchone()
                if row:
                    return jsonify({"answer": f"Bus {busnum} ({row[0]}) nominal kV: {row[1]}"} )
                else:
                    return jsonify({"answer": f"No info found for bus {busnum}."})

        return jsonify({"answer": f"Sorry, I can't answer that yet. You asked: {question}"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"answer": f"Error querying DB: {e}"})

    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
