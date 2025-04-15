from flask import Response
import mysql.connector
import pandas as pd

class ShowClgDetails:
    def __init__(self, logging, conn):
        self.logging = logging
        self.conn = conn
        self.data = ""
        self.status = 200
        self.fetch_colleges()

    def fetch_colleges(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM College_Details")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            df = pd.DataFrame(rows, columns=columns)
            self.data = df.to_html(index=False, classes='table table-striped', border=0)
            self.logging.info("College table fetched and converted to HTML successfully")
        except mysql.connector.Error as e:
            self.status = 500
            self.data = f"<h3>Error fetching college data: {str(e)}</h3>"
            self.logging.error(f"Error fetching college data: {e}")
        finally:
            cursor.close()

    def response(self):
        return Response(self.data, mimetype='text/html'), self.status

    def __del__(self):
        try:
            self.conn.close()
        finally:
            pass
