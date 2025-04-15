import bcrypt
from flask import jsonify
import mysql.connector


class AddUser:
    def __init__(self, request, logging, conn):
        self.request = request
        self.logging = logging
        self.conn = conn
        self.data = request.json
        self.success = True
        self.message = ''
        self.status = 200
        self.username = ''
        self.member_id = None

        self.check_keys()
        if self.success:
            self.add_user()
        if self.success:
            self.add_group_mapping()  # Optional logic if needed
        if self.success:
            self.create_login()

    def response(self):
        return jsonify(self.message), self.status    

    def check_keys(self):
        required_keys = ['username', 'password', 'role', 'email', 'session_id', 'DoB']
        for key in required_keys:
            if key not in self.data:
                self.success = False
                self.message = {'error': f'Bad request: {key} not found'}
                self.status = 400
                return

    def add_user(self):
        self.username = self.data['username']
        self.email = self.data['email']
        self.DoB = self.data['DoB']

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM members WHERE UserName = %s;", (self.username,))
            existing_user = cursor.fetchone()

            if existing_user:
                self.member_id = existing_user[0]  # Assuming ID is the first column
                self.logging.info(f"User {self.username} already exists with ID {self.member_id}")
                return
            else:
                cursor.execute(
                    "INSERT INTO members (UserName, emailID, DoB) VALUES (%s, %s, %s);",
                    (self.username, self.email, self.DoB)
                )
                self.conn.commit()
                self.logging.info(f"User {self.username} added to members table")
        except mysql.connector.Error as e:
            self.success = False
            self.logging.error(f"MySQL Error during add_user: {e}")
            self.message = {'error': str(e)}
            self.status = 500
        finally:
            cursor.close()

    def add_group_mapping(self):
        # Placeholder for group mapping logic
        pass

    def create_login(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT ID FROM members WHERE UserName = %s;", (self.username,))
            result = cursor.fetchone()

            if not result:
                self.success = False
                self.message = {'error': 'User not found in members table during login creation'}
                self.status = 404
                return

            self.member_id = result[0]
            hashed_password = bcrypt.hashpw(self.data['password'].encode(), bcrypt.gensalt())

            # Insert into Login table
            cursor.execute(
                "INSERT INTO Login (MemberID, Password, Role) VALUES (%s, %s, %s);",
                (self.member_id, hashed_password, self.data['role'])
            )
            self.conn.commit()
            self.logging.info(f"User {self.username} added to login table")
            self.message = {'message': 'User added successfully'}
            self.status = 200

        except Exception as e:
            self.success = False
            self.message = {'error': f'Failed to add user to login table: {str(e)}'}
            self.status = 500
            self.logging.error(f"Error adding user to login table: {e}")
        finally:
            cursor.close()

    def __del__(self):
        try:
            self.conn.close()
        except:
            pass
