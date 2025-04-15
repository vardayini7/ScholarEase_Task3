from flask import jsonify
import psycopg2

class UpdateImage:
    def __init__(self, request, conn, logging):
        # self.image_path = request
        self.conn = conn
        self.request =  request
        self.logging = logging
        
    def response(self):
        return jsonify(self.message), self.status

    def update_image(self):
        imagefile = self.request.files['image']
        member_id = self.request.form.get('member_id')

        if not member_id:
            return jsonify({'error': 'Missing member ID'}), 400

        if imagefile.filename == '':
            return jsonify({'error': 'Bad request: No image file selected'}), 400

        image_data = imagefile.read()

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO images (MemberID, image) VALUES (%s, %s)",
                (member_id, psycopg2.Binary(image_data))  # use just image_data if using MySQL
            )
            self.conn.commit()
            cursor.close()
            self.conn.close()
            self.logging.info(f"Image for member {member_id} added successfully")
            return jsonify({'message': 'Image uploaded successfully'}), 200

        except Exception as e:
            self.logging.error(f"Image upload failed: {str(e)}")
            return jsonify({'error': str(e)}), 500