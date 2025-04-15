# create_member.py
from flask import request, jsonify
from utils import get_db_connection

def create_member_route(app):
    @app.route('/create_member', methods=['POST'])
    def create_member():
        data = request.get_json()
        username = data.get('username')
        memberid = data.get('id')         # Provided by client; used as MemberID
        emailid = data.get('emailid')
        dob = data.get('dob')

        if not all([username, memberid, emailid, dob]):
            return jsonify({"error": "Missing fields"}), 400

        try:
            conn = get_db_connection(cims=True)
            cursor = conn.cursor()

            # Insert into Members table (centralized)
            cursor.execute("""
                INSERT INTO members (UserName, ID, emailID, DoB)
                VALUES (%s, %s, %s, %s)
            """, (username, memberid, emailid, dob))

            # Insert default credentials into Login table
            cursor.execute("""
                INSERT INTO Login (Password, MemberID, Session, Expiry, Role)
                VALUES (%s, %s, NULL, NULL, %s)
            """, ('admin123', memberid, 'admin'))  # For example, creating an admin; adjust as needed
            conn.commit()
            return jsonify({"message": "Member and login created successfully"}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            conn.close()
