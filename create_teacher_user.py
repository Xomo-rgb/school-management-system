import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.security import generate_password_hash
from datetime import datetime

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Teacher user data
teacher_data = {
    'full_name': 'Test Teacher',
    'email': 'teacher@harmonyschool.com',
    'password': generate_password_hash('teacher123'),
    'role': 'teacher',
    'must_reset_password': True,
    'created_at': datetime.now()
}

# Add to harmony-school
school_id = 'harmony-school'
users_ref = db.collection('schools').document(school_id).collection('users')
users_ref.add(teacher_data)

print("Teacher user created successfully!")
print("Email: teacher@harmonyschool.com")
print("Password: teacher123")
print("Role: teacher")
