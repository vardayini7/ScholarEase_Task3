# scholarship_api.py
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import mysql.connector
import logging
from utils import get_db_connection, validate_session, is_admin, log_unauthorized_access

scholarship_bp = Blueprint('scholarship_bp', __name__)

# GET /scholarship - get all scholarships (valid session required)
@scholarship_bp.route('/scholarship', methods=['GET'])
def get_scholarship():
    session_token = request.headers.get('Authorization')
    if not session_token or not validate_session(session_token):
        log_unauthorized_access("GET scholarship", f"Token: {session_token}")
        return jsonify({"error": "Invalid or missing session token"}), 401

    try:
        conn = get_db_connection(cims=False)  # project-specific db for scholarship data
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Scholarship")
        scholarships = cursor.fetchall()
        return jsonify({"scholarships": scholarships}), 200
    except mysql.connector.Error as e:
        logging.error(f"Error fetching scholarships: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# POST /scholarship - admin only: create a new scholarship record
@scholarship_bp.route('/scholarship', methods=['POST'])
def create_scholarship():
    session_token = request.headers.get('Authorization')
    if not session_token or not is_admin(session_token):
        log_unauthorized_access("Create scholarship", f"Token: {session_token}")
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    name = data.get("name")
    description = data.get("description")
    amount = data.get("amount")
    deadline = data.get("deadline")   # Expected format: 'YYYY-MM-DD'

    if not name or not amount:
        return jsonify({"error": "Missing scholarship name or amount"}), 400

    try:
        conn = get_db_connection(cims=False)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Scholarship (Name, Description, Amount, Deadline, CreatedAt)
            VALUES (%s, %s, %s, %s, NOW())
        """, (name, description, amount, deadline))
        conn.commit()
        return jsonify({"message": "Scholarship created successfully"}), 201
    except mysql.connector.Error as e:
        logging.error(f"Error creating scholarship: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# PUT /scholarship/<id> - admin only: update an existing scholarship
@scholarship_bp.route('/scholarship/<int:scholarship_id>', methods=['PUT'])
def update_scholarship(scholarship_id):
    session_token = request.headers.get('Authorization')
    if not session_token or not is_admin(session_token):
        log_unauthorized_access("Update scholarship", f"Token: {session_token}, ScholarshipID: {scholarship_id}")
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    new_name = data.get("name")
    new_description = data.get("description")
    new_amount = data.get("amount")
    new_deadline = data.get("deadline")

    if not any([new_name, new_description, new_amount, new_deadline]):
        return jsonify({"error": "No update fields provided"}), 400

    try:
        conn = get_db_connection(cims=False)
        cursor = conn.cursor()
        update_fields = []
        update_values = []

        if new_name:
            update_fields.append("Name = %s")
            update_values.append(new_name)
        if new_description:
            update_fields.append("Description = %s")
            update_values.append(new_description)
        if new_amount:
            update_fields.append("Amount = %s")
            update_values.append(new_amount)
        if new_deadline:
            update_fields.append("Deadline = %s")
            update_values.append(new_deadline)

        update_values.append(scholarship_id)
        query = "UPDATE Scholarship SET " + ", ".join(update_fields) + " WHERE ID = %s"
        cursor.execute(query, update_values)
        conn.commit()
        return jsonify({"message": f"Scholarship {scholarship_id} updated successfully"}), 200
    except mysql.connector.Error as e:
        logging.error(f"Error updating scholarship: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# DELETE /scholarship/<id> - admin only: delete a scholarship
@scholarship_bp.route('/scholarship/<int:scholarship_id>', methods=['DELETE'])
def delete_scholarship(scholarship_id):
    session_token = request.headers.get('Authorization')
    if not session_token or not is_admin(session_token):
        log_unauthorized_access("Delete scholarship", f"Token: {session_token}, ScholarshipID: {scholarship_id}")
        return jsonify({"error": "Admin access required"}), 403

    try:
        conn = get_db_connection(cims=False)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Scholarship WHERE ID = %s", (scholarship_id,))
        conn.commit()
        return jsonify({"message": f"Scholarship {scholarship_id} deleted successfully"}), 200
    except mysql.connector.Error as e:
        logging.error(f"Error deleting scholarship: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
