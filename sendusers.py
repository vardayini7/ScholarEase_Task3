import mysql.connector
import bcrypt
import ShowClgDetails  # Add this with your other imports

# Database connection for your project database (adjust if needed)
conn = mysql.connector.connect(
    host="10.0.116.125",
    user="cs432g16",
    password="LbNXp7Tz",
    database="cs432g16"
)
cursor = conn.cursor()

# User details
username = "john123"
plaintext_password = "johnspassword"
role = "user"

# Insert into members table
cursor.execute("INSERT INTO members (UserName) VALUES (%s)", (username,))
member_id = cursor.lastrowid  # Get the auto-generated member ID

# Hash password using bcrypt
hashed_password = bcrypt.hashpw(plaintext_password.encode(), bcrypt.gensalt()).decode()

# Insert into Login table
cursor.execute(
    "INSERT INTO Login (MemberID, Password, Role) VALUES (%s, %s, %s)",
    (member_id, hashed_password, role)
)

conn.commit()
print(f"User '{username}' added with MemberID: {member_id}")
cursor.close()
conn.close()
