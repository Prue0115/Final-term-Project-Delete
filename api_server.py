from flask import Flask, request, jsonify
import pymysql
import datetime

app = Flask(__name__)

DB_CONFIG = {
    'host': '172.30.1.41',
    'user': 'User',
    'password': '8iHE4ow16u8iPoqOdO3i271OLiMuHo',
    'db': 'lockerdb',
    'charset': 'utf8mb4'
}

@app.route("/save_user", methods=["POST"])
def save_user():
    data = request.json
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute(
            "INSERT INTO user_info (created_at, student_id, password, timer_min, hint) VALUES (%s, %s, %s, %s, %s)",
            (now, data["student_id"], data["password"], data["timer_min"], data["hint"])
        )
        conn.commit()
        conn.close()
        return jsonify({"result": "ok"})
    except Exception as e:
        return jsonify({"result": "error", "msg": str(e)}), 500

@app.route("/get_user", methods=["POST"])
def get_user():
    data = request.json
    student_id = data.get("student_id")
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute(
            "SELECT password, hint, timer_min FROM user_info WHERE student_id = %s ORDER BY created_at DESC LIMIT 1",
            (student_id,)
        )
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify({
                "result": "ok",
                "user": {
                    "password": row[0],
                    "hint": row[1],
                    "timer_min": row[2]
                }
            })
        else:
            return jsonify({"result": "not_found"}), 404
    except Exception as e:
        return jsonify({"result": "error", "msg": str(e)}), 500

@app.route("/check_update", methods=["GET"])
def check_update():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute("SELECT version, download_url FROM update_info ORDER BY version DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            return jsonify({"latest_version": row[0], "download_url": row[1]})
        else:
            return jsonify({"result": "not_found"}), 404
    except Exception as e:
        return jsonify({"result": "error", "msg": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)