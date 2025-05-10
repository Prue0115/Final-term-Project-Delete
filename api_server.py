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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)