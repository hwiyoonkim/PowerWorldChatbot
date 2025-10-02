import os
import sqlite3
import traceback
import re
import csv
from flask import Flask, request, jsonify, render_template, Response
from werkzeug.utils import secure_filename
from win32com.client import Dispatch
import pythoncom

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# -----------------------------
# DB utils
# -----------------------------
def init_db():
    conn = sqlite3.connect('caseinfo.db')
    c = conn.cursor()
    # wipe all tables cleanly
    c.execute("PRAGMA writable_schema = 1;")
    c.execute("DELETE FROM sqlite_master WHERE type IN ('table','index','trigger');")
    c.execute("PRAGMA writable_schema = 0;")
    conn.commit()
    conn.close()


def ensure_text(x):
    return "" if x is None else str(x)


# -----------------------------
# SimAuto -> SQLite helpers
# -----------------------------
def transpose_simauto(data, fields):
    """
    PowerWorld often returns data as column-major:
      data = [ [values_for_field1], [values_for_field2], ... ]
    We need to transpose -> rows per element.
    """
    if not data:
        return []

    column_major = (
        len(data) == len(fields) and
        all(hasattr(col, "__iter__") and not isinstance(col, (str, bytes)) for col in data)
    )

    if column_major:
        n_elems = min(len(col) for col in data) if data else 0
        rows = []
        for i in range(n_elems):
            row = [data[f_idx][i] if i < len(data[f_idx]) else None for f_idx in range(len(fields))]
            rows.append(row)
        return rows
    else:
        return [r[:len(fields)] for r in data]


def is_valid_row(obj, fields, row):
    """Reject header/junk rows based on expected key columns"""
    try:
        if obj == "Bus":
            return str(row[0]).strip().isdigit() and len(str(row[1]).strip()) > 0
        elif obj == "Gen":
            return str(row[0]).strip().isdigit() and len(str(row[1]).strip()) > 0
        elif obj == "Load":
            return str(row[0]).strip().isdigit() and len(str(row[1]).strip()) > 0
        elif obj == "Branch":
            return str(row[0]).strip().isdigit() and str(row[1]).strip().isdigit() and len(str(row[2]).strip()) > 0
        else:
            return True
    except Exception:
        return False


def extract_and_store_case_data(pw):
    """
    Extract selected stable fields and store into SQLite.
    Now transposes SimAuto output (column-major -> row-major) and validates rows.
    """
    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()

    schema = {
        "Bus":    ["BusNum", "BusName", "NomKV",     "AreaNum", "ZoneNum"],
        "Gen":    ["BusNum", "GenID",   "GenMW",     "GenMvar", "Status"],
        "Load":   ["BusNum", "LoadID",  "LoadMW",    "LoadMvar","Status"],
        "Branch": ["BusNum", "BusNum:1","LineCircuit","MW",     "Mvar",   "Status"],
    }

    for obj, fields in schema.items():
        try:
            print(f"Extracting {obj} with fields: {fields}")
            result, data = pw.GetParametersMultipleElement(obj, fields, "")
            if result != "":
                print(f"⚠️ Could not get {obj} data: {result}")
                continue

            col_defs = ", ".join([f'"{f}" TEXT' for f in fields])
            c.execute(f'CREATE TABLE IF NOT EXISTS "{obj}" ({col_defs})')

            rows = transpose_simauto(data, fields)

            placeholders = ", ".join(["?"] * len(fields))
            insert_sql = f'INSERT INTO "{obj}" VALUES ({placeholders})'

            inserted = 0
            for row in rows:
                if not is_valid_row(obj, fields, row):
                    continue
                clean_row = [ensure_text(x) for x in row[:len(fields)]]
                if len(clean_row) == len(fields):
                    c.execute(insert_sql, clean_row)
                    inserted += 1
            print(f"Inserted {inserted} {obj} rows")

        except Exception as e:
            print(f"Error extracting {obj}: {e}")
            traceback.print_exc()

    conn.commit()
    conn.close()


# -----------------------------
# Routes
# -----------------------------
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


@app.route('/view/<table>')
def view_table(table):
    """Render the whole table as HTML (no row limit)."""
    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()
    try:
        c.execute(f'SELECT * FROM "{table}"')
        rows = c.fetchall()
        cols = [desc[0] for desc in c.description]
    except Exception as e:
        return f"<h3>Error: {e}</h3>"
    finally:
        conn.close()

    html = f"<h2>{table} (rows: {len(rows)})</h2>"
    html += f'<p><a href="/download/{table}">Download {table} as CSV</a> | <a href="/">Back</a></p>'
    html += "<div style='overflow:auto; max-height:75vh; border:1px solid #ddd;'>"
    html += "<table border='1' cellpadding='5' style='border-collapse:collapse; width:100%;'>"
    html += "<tr>" + "".join([f"<th>{col}</th>" for col in cols]) + "</tr>"
    for row in rows:
        html += "<tr>" + "".join([f"<td>{'' if v is None else v}</td>" for v in row]) + "</tr>"
    html += "</table></div>"
    return html


@app.route('/download/<table>')
def download_table(table):
    """Download a table as CSV."""
    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()
    try:
        c.execute(f'SELECT * FROM "{table}"')
        rows = c.fetchall()
        cols = [desc[0] for desc in c.description]
    except Exception as e:
        conn.close()
        return f"<h3>Error: {e}</h3>"
    finally:
        conn.close()

    def generate_csv():
        yield ",".join(cols) + "\n"
        for row in rows:
            yield ",".join([("" if v is None else str(v)) for v in row]) + "\n"

    return Response(
        generate_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={table}.csv"}
    )


@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json() or {}
    question = (data.get("question") or data.get("query") or "").lower().strip()

    conn = sqlite3.connect("caseinfo.db")
    c = conn.cursor()

    try:
        # --- Summarize the case ---
        if "summarize" in question or "summary" in question:
            parts = {}
            for table in ["Bus", "Gen", "Load", "Branch"]:
                try:
                    c.execute(f'SELECT COUNT(*) FROM "{table}"')
                    parts[table] = c.fetchone()[0]
                except:
                    parts[table] = 0
            return jsonify({"answer":
                f"This case contains {parts['Bus']} buses, "
                f"{parts['Gen']} generators, "
                f"{parts['Load']} loads, and "
                f"{parts['Branch']} branches."
            })

        # --- Counts ---
        if "how many buses" in question or ("number" in question and "bus" in question):
            c.execute('SELECT COUNT(*) FROM "Bus"')
            count = c.fetchone()[0]
            return jsonify({"answer": f"There are {count} buses in this case."})

        if "how many gen" in question or "how many generators" in question:
            c.execute('SELECT COUNT(*) FROM "Gen"')
            count = c.fetchone()[0]
            return jsonify({"answer": f"There are {count} generators in this case."})

        if "how many loads" in question:
            c.execute('SELECT COUNT(*) FROM "Load"')
            count = c.fetchone()[0]
            return jsonify({"answer": f"There are {count} loads in this case."})

        if "how many branch" in question or "how many lines" in question:
            c.execute('SELECT COUNT(*) FROM "Branch"')
            count = c.fetchone()[0]
            return jsonify({"answer": f"There are {count} branches (lines) in this case."})

        # --- Bus kV queries ---
        if "bus" in question and "kv" in question:
            m = re.search(r'bus\s+(\d+)', question)
            if m:
                busnum = m.group(1)
                c.execute('SELECT "BusName","NomKV" FROM "Bus" WHERE "BusNum"=?', (busnum,))
                row = c.fetchone()
                if row:
                    return jsonify({"answer": f"Bus {busnum} ({row[0]}) operates at {row[1]} kV"} )
                else:
                    return jsonify({"answer": f"No info found for bus {busnum}."})

        # --- Default fallback ---
        return jsonify({"answer": f"Sorry, I can’t answer that yet. You asked: {question}"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"answer": f"Error querying DB: {e}"})

    finally:
        conn.close()


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
