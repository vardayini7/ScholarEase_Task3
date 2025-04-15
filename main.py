from flask import Flask, request, jsonify, send_from_directory 
import mysql.connector
import logging
import os
import uuid
from datetime import datetime, timedelta
import ShowScholarships  # Custom class to handle the logic
import ShowClgDetails
from Apply_Scholarship import ApplyScholarship
import ShowBankDetails
import ShowAlumni
import ShowStats
from utils import validate_session,get_db_connection,log_change


app = Flask(__name__)
app.config['SECRET_KEY'] = 'CS'  

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='a'
)

# Database Configuration
db_config_proj = {
    "host": "10.0.116.125",
    "user": "cs432g16",
    "password": "LbNXp7Tz",
    "database": "cs432g16"
}

db_config_cism = {
    "host": "10.0.116.125",
    "user": "cs432g16", 
    "password": "LbNXp7Tz",
    "database": "cs432cims"
}

def get_db_connection(cims=True):
    """Establish a database connection."""
    if cims:
        return mysql.connector.connect(**db_config_cism)
    else:
        return mysql.connector.connect(**db_config_proj)

@app.route('/show_scholarship', methods=['GET'])
def show_scholarship():
    print(" /show_scholarship route hit")
    try:
        conn = get_db_connection(cims=False)
        print("Connected to cs432g16")
        scholarship = ShowScholarships.ShowScholarships(logging, conn)
        return scholarship.response()
    except Exception as e:
        print(f" ERROR in /show_scholarship: {e}")
        return f"<h3>Server Error: {e}</h3>", 500

@app.route('/', methods=['GET'])
def frontend():
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/api/hello', methods=['GET'])
def hello():
    return jsonify({"message": "Welcome to the Scholarship API"}), 200

@app.route('/show_colleges', methods=['GET'])
def show_colleges():
    college = ShowClgDetails.ShowClgDetails(logging, get_db_connection(cims=False))
    return college.response()

@app.route("/Apply_Scholarship", methods=["POST"])
def apply_scholarship():
    print(" /Apply_Scholarship route hit")
    try:
        conn = get_db_connection(cims=False)
        print("Connected to database")
        data = request.get_json()
        application = ApplyScholarship(logging, conn, data)
        return jsonify(application.response())
    except Exception as e:
        print(f"ERROR in /Apply_Scholarship: {e}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/generate_app_id", methods=["GET"])
def generate_app_id():
    try:
        conn = get_db_connection(cims=False)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(Application_ID) FROM Application")  # Match your insert
        result = cursor.fetchone()
        next_id = (result[0] or 0) + 1
        cursor.close()
        return jsonify({"Application_ID": next_id})
    except Exception as e:
        print(f"Error generating application ID: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/create_member', methods=['POST'])
def create_member():
    data = request.get_json()

    username = data.get('username')
    memberid = data.get('id')         # Used as memberid in login table
    emailid = data.get('emailid')
    dob = data.get('dob')
    

    if not all([username, memberid, emailid, dob]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = get_db_connection(cims=True)  
        cursor = conn.cursor()

        # Insert into Members table
        cursor.execute("""
            INSERT INTO members (UserName, ID, emailID, DoB)
            VALUES (%s, %s, %s, %s)
        """, (username, memberid, emailid, dob))

        # Insert default credentials into login table
        cursor.execute("""
            INSERT INTO Login (Password, MemberID, Session, Expiry, Role)
            VALUES (%s, %s, NULL, NULL, %s)
        """, ('admin123', memberid, 'admin'))

        conn.commit()
        return jsonify({"message": "Member and login created successfully"}), 201

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

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

        # Validate credentials
        cursor.execute("SELECT * FROM Login WHERE MemberID = %s AND Password = %s", (member_id, password))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid MemberID or Password"}), 401

        # Generate new session token and expiry timestamp (as INT)
        session_token = str(uuid.uuid4())
        expiry_time = int((datetime.now() + timedelta(hours=1)).timestamp())

        # Update session in the login table
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

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# Helper function to check admin authorization
def is_admin_authorized(session_token):
    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT Role FROM Login
            WHERE Session = %s AND Expiry > %s
        """, (session_token, int(datetime.now().timestamp())))

        result = cursor.fetchone()
        return result and result['Role'] == 'admin'

    except mysql.connector.Error as e:
        logging.error(f"Authorization check failed: {e}")
        return False

    finally:
        cursor.close()
        conn.close()

def get_session(token):
    conn = get_db_connection(cims=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Login WHERE Session = %s", (token,))
        session = cursor.fetchone()
        return session
    finally:
        cursor.close()
        conn.close()

# ADMIN: Add a new member (similar to create_member but admin-authenticated)
@app.route('/admin/add_member', methods=['POST'])
def admin_add_member():
    session_token = request.headers.get('Authorization')
    session = get_session(session_token)
    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403

    performed_by = session.get("MemberID")
    data = request.get_json()
    username = data.get('username')
    emailid = data.get('emailid')
    dob = data.get('dob')
    role = data.get('role', 'member')
    image_link = data.get('image_link')
    group_id = data.get('group_id')

    if not all([username, emailid, dob, image_link, group_id]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor()

        # Check if the username already exists
        cursor.execute("SELECT ID FROM members WHERE UserName = %s", (username,))
        existing_member = cursor.fetchone()

        if existing_member:
            # Username exists → insert only into MemberGroupMapping
            memberid = existing_member[0]

            # Check if the mapping already exists to avoid duplicates
            cursor.execute("""
                SELECT * FROM MemberGroupMapping WHERE MemberID = %s AND GroupID = %s
            """, (memberid, group_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO MemberGroupMapping (MemberID, GroupID)
                    VALUES (%s, %s)
                """, (memberid, group_id))
                conn.commit()
                description = f"Admin {performed_by} added new member {memberid} ({username}, {role})"
                log_change(
                    performed_by=performed_by,
                    action_type="ADD",
                    table_name="members",
                    description=description
                )
                return jsonify({"message": "Existing member added to new group successfully."}), 200
            else:
                return jsonify({"message": "Member already mapped to this group."}), 200
        else:
            # Username does not exist → proceed with full member creation
            cursor.execute("SELECT IFNULL(MAX(ID), 0) + 1 FROM members")
            memberid = cursor.fetchone()[0]

            # Insert into members
            cursor.execute("""
                INSERT INTO members (UserName, ID, emailID, DoB)
                VALUES (%s, %s, %s, %s)
            """, (username, memberid, emailid, dob))

            # Insert into login
            cursor.execute("""
                INSERT INTO Login (Password, MemberID, Session, Expiry, Role)
                VALUES (%s, %s, NULL, NULL, %s)
            """, ('default123', memberid, role))

            # Insert into images
            cursor.execute("""
                INSERT INTO images (MemberID, ImagePath)
                VALUES (%s, %s)
            """, (memberid, image_link))

            # Insert into MemberGroupMapping
            cursor.execute("""
                INSERT INTO MemberGroupMapping (MemberID, GroupID)
                VALUES (%s, %s)
            """, (memberid, group_id))

            conn.commit()
            description = f"Admin {performed_by} added new member {memberid} ({username}, {role})"
            log_change(
                    performed_by=performed_by,
                    action_type="ADD",
                    table_name="members",
                    description=description
                )
            return jsonify({"message": "New member added successfully with image and group mapping."}), 201

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/admin/access_data', methods=['GET'])
def admin_access_data():
    session_token = request.headers.get('Authorization')

    # Only allow access to admins
    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        # Example: fetch all members as sample protected data
        conn = get_db_connection(cims=True)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM members")
        data = cursor.fetchall()

        return jsonify({
            "message": "Admin access granted",
            "data": data
        }), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

def get_session(token):
    conn = get_db_connection(cims=True)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Login WHERE Session = %s", (token,))
        session = cursor.fetchone()
        return session
    finally:
        cursor.close()
        conn.close()
from utils import log_change
# ADMIN: Delete a member
@app.route('/admin/delete_member/<member_id>', methods=['DELETE'])
def admin_delete_member(member_id):
    session_token = request.headers.get('Authorization')
    session = get_session(session_token)

    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403
    performed_by = session.get("MemberID")  # Admin who performed the deletion
    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor()

        # Check how many groups this member is in
        cursor.execute("SELECT COUNT(*) FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
        group_count = cursor.fetchone()[0]

        if group_count > 1:
            # Just remove the mapping with GroupID = 16
            cursor.execute("""
                DELETE FROM MemberGroupMapping 
                WHERE MemberID = %s AND GroupID = 16
            """, (member_id,))
            conn.commit()
            # log_change(
            # performed_by=performed_by,
            # action_type="DELETE",
            # table_name="members",
            # # description=f"Admin {performed_by} deleted member {member_id}. Details: {member_details}")
            return jsonify({"message": f"Member {member_id} removed from GroupID 16 only (still in other groups)"}), 200

        else:
            # Fully delete the member
            cursor.execute("DELETE FROM Login WHERE MemberID = %s", (member_id,))
            cursor.execute("DELETE FROM images WHERE MemberID = %s", (member_id,))
            cursor.execute("DELETE FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
            cursor.execute("DELETE FROM members WHERE ID = %s", (member_id,))
            conn.commit()
        #     log_change(
        #     performed_by=performed_by,
        #     action_type="DELETE",
        #     table_name="members",
        # #     description=f"Admin {performed_by} deleted member {member_id}. Details: {member_details}"
        # # )
            return jsonify({"message": f"Member {member_id} deleted from all tables"}), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/show_profile/<userid>')
def show_profile(userid):
    from ShowProfile import ShowProfile
    conn = get_db_connection(cims=True)
    sp = ShowProfile(logging, conn, userid)
    return sp.response()


# ADMIN: Get all member details
@app.route('/admin/get_members', methods=['GET'])
def admin_get_members():
    session_token = request.headers.get('Authorization')
    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403

    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM members")
        members = cursor.fetchall()

        return jsonify(members), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# ADMIN: Update member details
@app.route('/admin/update_member/<member_id>', methods=['PUT'])
def admin_update_member(member_id):
    session_token = request.headers.get('Authorization')
    if not is_admin_authorized(session_token):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    username = data.get('username')
    emailid = data.get('emailid')
    dob = data.get('dob')

    if not any([username, emailid, dob]):
        return jsonify({"error": "No update fields provided"}), 400

    try:
        conn = get_db_connection(cims=True)
        cursor = conn.cursor()

        if username:
            cursor.execute("UPDATE members SET UserName = %s WHERE ID = %s", (username, member_id))
        if emailid:
            cursor.execute("UPDATE members SET emailID = %s WHERE ID = %s", (emailid, member_id))
        if dob:
            cursor.execute("UPDATE members SET DoB = %s WHERE ID = %s", (dob, member_id))

        conn.commit()
        return jsonify({"message": f"Member {member_id} updated successfully"}), 200

    except mysql.connector.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# Dummy route to get members (only if token matches)
@app.route('/admin/get_members', methods=['GET'])
def get_members():
    token = request.headers.get("Authorization")
    if token != "dummy_admin_token":
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection(cims=True)  # Note: cims=True for cs432cims
        cursor = conn.cursor(dictionary=True)  # returns results as dicts

        cursor.execute("SELECT * FROM members")
        members = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(members)
    except Exception as e:
        print(f"Error fetching members: {e}")
        return jsonify({"error": "Failed to fetch members"}), 500
    
@app.route('/application/status', methods=['GET'])
def check_application_status():
    application_id = request.args.get('application_id')

    if not application_id:
        return jsonify({"error": "Application ID is required"}), 400

    try:
        conn = get_db_connection(cims=False)
        cursor = conn.cursor()

        cursor.execute("SELECT Status FROM Status WHERE Application_ID = %s", (application_id,))
        result = cursor.fetchone()

        if result:
            status = result[0]
            return jsonify({
                "Application_ID": application_id,
                "Status": status
            }), 200
        else:
            return jsonify({"error": "Application ID not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/member.html')
def serve_member_page():
    return send_from_directory(os.getcwd(), 'member.html')

@app.route('/admin.html')
def serve_admin_page():
    return send_from_directory(os.getcwd(), 'admin.html')

@app.route('/show_bank_details', methods=['GET'])
def show_banks():
    college = ShowBankDetails.ShowBankDetails(logging, get_db_connection(cims=False))
    return college.response()



@app.route('/show_alumni_details', methods=['GET'])
def show_alumni():
    college = ShowAlumni.ShowAlumni(logging, get_db_connection(cims=False))
    return college.response()

@app.route('/show_stats_details', methods=['GET'])
def show_stats():
    college = ShowStats.ShowStats(logging, get_db_connection(cims=False))
    return college.response()


if __name__ == '__main__':
    try:
        conn = get_db_connection(cims=False)  # ⚠ Connect to correct DB
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE()")
        logging.info(f"Connected to database: {cursor.fetchone()[0]}")
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"DB connection failed on startup: {e}")

    app.run(debug=True)


