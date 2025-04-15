from flask import Response
import mysql.connector
import pandas as pd

class ShowProfile:
    def __init__(self, logging, conn, userid):
        self.logging = logging
        self.conn = conn
        self.userid = userid  # Filter condition
        self.data = ""
        self.status = 200
        self.fetch_member_profile()

    def fetch_member_profile(self):
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM members WHERE ID = %s"
            cursor.execute(query, (self.userid,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            if rows:
                df = pd.DataFrame(rows, columns=columns)
                self.data = df.to_html(index=False, classes='table table-striped', border=0)
                self.logging.info(f"Member profile fetched for ID: {self.userid}")
            else:
                self.data = f"<h3>No member found with ID {self.userid}</h3>"
                self.status = 404
                self.logging.warning(f"No member found with ID: {self.userid}")

        except mysql.connector.Error as e:
            self.status = 500
            self.data = f"<h3>Error fetching member data: {str(e)}</h3>"
            self.logging.error(f"Error fetching member data: {e}")
        finally:
            cursor.close()

    def response(self):
        return Response(self.data, mimetype='text/html'), self.status

    def __del__(self):
        try:
            self.conn.close()
        finally:
            pass