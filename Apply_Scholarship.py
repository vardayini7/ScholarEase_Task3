# Apply_Scholarship.py
import datetime

class ApplyScholarship:
    def __init__(self, logging, conn, form_data):
        self.logging = logging
        self.conn = conn
        self.form_data = form_data

    def generate_application_id(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(Application_ID) FROM Application")  # Replace 'Applications' with your table name
        result = cursor.fetchone()
        cursor.close()
        return (result[0] or 0) + 1
    
    def check_eligibility_and_set_status(self, app_id, funding_id, gender, cpi):
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT Gender, Min_CPI FROM Eligibility WHERE Funding_ID = %s
        """, (funding_id,))
        result = cursor.fetchone()

        if result:
            allowed_gender, min_cpi = result

            # Handle NA (any gender allowed)
            gender_match = (allowed_gender == "NA") or (allowed_gender == gender)
            cpi_match = (min_cpi is None) or (cpi >= float(min_cpi))

            status = "Approved" if gender_match and cpi_match else "Rejected"

            cursor.execute("""
                INSERT INTO Status (Application_ID, Type, Status)
                VALUES (%s, %s, %s)
            """, (app_id, 'Scholarship', status))

            self.conn.commit()
        cursor.close()

    def response(self):
        try:
            cursor = self.conn.cursor()

            app_id = self.generate_application_id()
            student_id = int(self.form_data["Student_ID"])
            funding_id = self.form_data["Funding_ID"]
            name = self.form_data["Student_Name"]
            gender = self.form_data["Student_Gender"]
            income = float(self.form_data["Student_Annual_Income"] or 0)
            cpi = float(self.form_data["Student_CPI"] or 0)
            submission_date = datetime.date.today()

            #Step 1: Fetch student info from college_details
            cursor.execute("""
                SELECT Student_Name, Gender, Annual_Income, CPI FROM College_Details WHERE Student_ID = %s
            """, (student_id,))
            db_record = cursor.fetchone()

            if not db_record:
                cursor.close()
                return {"error": "Student ID not found in college records"}

            db_name, db_gender, db_income, db_cpi = db_record

            # Step 2: Match all fields
            if (db_name != name or
                db_gender != gender or
                float(db_income) != income or
                float(db_cpi) != cpi):
                
                cursor.close()
                return {"error": "data not matching with the college data, pls update"}

            #Step 3: Insert into Application
            cursor.execute("""
                INSERT INTO Application
                (Application_ID, Student_ID, Funding_ID, Student_Name, Student_Gender, Student_Annual_Income, Student_CPI, Submission_Date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (app_id, student_id, funding_id, name, gender, income, cpi, submission_date))

            self.conn.commit()
            cursor.close()

            # Step 4: Check eligibility and update status
            self.check_eligibility_and_set_status(app_id, funding_id, gender, cpi)

            return {"message": f"Application submitted successfully! Application ID: {app_id}"}

        except Exception as e:
            self.logging.error(f"Error in ApplyScholarship.response: {e}")
            return {"error": str(e)}

