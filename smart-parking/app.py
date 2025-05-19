from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

# Fetch data from database
def fetch_logs():
    conn = sqlite3.connect("vehicle_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT plate_number, timestamp FROM logs ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()
    return logs

@app.route("/")
def index():
    logs = fetch_logs()
    return render_template("index.html", logs=logs)

if __name__ == "__main__":
    app.run(debug=True)
