import bcrypt
import mysql.connector
from flask import jsonify
import jwt
import datetime


class Login:
    def __init__(self, request, conn, logging, secret_key):
        self.data = request.json
        self.username = self.data.get('username')
        self.password = self.data.get('password')
        self.group = self.data.get('group')
        self.conn = conn
        self.logging = logging
        self.secret_key = secret_key
        self.success = True
        self.status = 200
        self.response = None

        if not self.username or not self.password:
            self.success = False
            self.response = jsonify({"error": "Username and password required"}), 400
            return

        self.get_member_id()
        if self.success:
            self.authenticate_user()

    def get_member_id(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT ID FROM members WHERE UserName = %s;", (self.username,))
            result = cursor.fetchone()
            cursor.close()

            if result:
                self.member_id = result[0]
            else:
                self.success = False
                self.response = jsonify({"error": f"User {self.username} does not exist"}), 404
        except mysql.connector.Error as e:
            self.success = False
            self.logging.error(f"MySQL Error in get_member_id: {e}")
            self.response = jsonify({"error": "Internal server error"}), 500

    def authenticate_user(self):
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("SELECT Password, Role FROM Login WHERE MemberID = %s", (self.member_id,))
            user = cursor.fetchone()
            cursor.close()

            if not user:
                self.response = jsonify({"error": "Invalid credentials"}), 401
                return

            stored_hash = user['Password'].encode('utf-8')

            if not bcrypt.checkpw(self.password.encode('utf-8'), stored_hash):
                self.response = jsonify({"error": "Invalid credentials"}), 401
                return

            expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            token = jwt.encode({
                "user": self.username,
                "role": user['Role'],
                "exp": expiry,
                "group": self.group,
                "session_id": self.member_id
            }, self.secret_key, algorithm="HS256")

            cursor = self.conn.cursor()
            cursor.execute(
                'UPDATE Login SET Session = %s, Expiry = %s WHERE MemberID = %s',
                (token, expiry.timestamp(), self.member_id)
            )
            self.conn.commit()
            cursor.close()

            self.response = jsonify({
                "message": "Login successful",
                "session_token": token,
                "max_age": 3600,
                "username": self.username,
                "group": self.group,
                "role": user['Role']
            }), 200

        except Exception as e:
            self.logging.error(f"Error in authenticate_user: {e}")
            self.response = jsonify({"error": "Internal server error"}), 500

    def get_response(self):
        return self.response
    
    def get_session(self):
        return self.response

