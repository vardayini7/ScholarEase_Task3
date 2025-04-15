@app.route('/admin/add_member', methods=['POST'])
def admin_add_member():
    session_token = request.headers.get('Authorization')
    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    username = data.get('username')
    memberid = data.get('id')
    emailid = data.get('emailid')
    dob = data.get('dob')
    role = data.get('role', 'member')  # Optional role

    if not all([username, memberid, emailid, dob]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO members (UserName, ID, emailID, DoB)
            VALUES (%s, %s, %s, %s)
        """, (username, memberid, emailid, dob))

        cursor.execute("""
            INSERT INTO Login (Password, MemberID, Session, Expiry, Role)
            VALUES (%s, %s, NULL, NULL, %s)
        """, ('default123', memberid, role))

        conn.commit()
        return jsonify({"message": "Member added by admin successfully"}), 201

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()