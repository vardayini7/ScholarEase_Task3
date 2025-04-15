# auth_user.py
from flask import request, jsonify
import uuid
from datetime import datetime, timedelta
from utils import get_db_connection

def auth_user_route(app):
    @app.route('/authUser', methods=['POST'])
    def auth_user():
        data = request.get_json()
        member_id = data.get('member_id')
        password = data.get('password')

        if not member_id or not password:
            return jsonify({"error": "Missing MemberID or Password"}), 400

        try:
            conn = get_db_connection(cims=True)
            cursor = conn.cursor(dictionary=True)

            # Validate credentials from Login table
            cursor.execute("SELECT * FROM Login WHERE MemberID = %s AND Password = %s", (member_id, password))
            user = cursor.fetchone()

            if not user:
                return jsonify({"error": "Invalid MemberID or Password"}), 401

            # Generate a new session token and expiry (here expiry is stored as INT - a UNIX timestamp)
            session_token = str(uuid.uuid4())
            expiry_time = int((datetime.now() + timedelta(hours=1)).timestamp())

            cursor.execute("""
                UPDATE Login
                SET Session = %s, Expiry = %s
                WHERE MemberID = %s
            """, (session_token, expiry_time, member_id))
            conn.commit()

            return jsonify({
                "message": "Login successful",
                "session_token": session_token,
                "expiry": expiry_time,
                "role": user['Role']
            }), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            conn.close()
