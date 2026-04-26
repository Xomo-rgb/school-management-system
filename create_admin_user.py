"""
Create initial admin user in Firebase
Run: python create_admin_user.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.security import generate_password_hash

cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

school_id = input("Enter school ID (default: harmony-school): ").strip() or "harmony-school"

admin_user = {
    'email': 'admin@harmonyschool.com',
    'password': generate_password_hash('admin123'),
    'full_name': 'System Administrator',
    'role': 'system_admin',
    'must_reset_password': True
}

db.collection('schools').document(school_id).collection('users').add(admin_user)

print(f"\n✓ Admin user created successfully!")
print(f"School ID: {school_id}")
print(f"Email: admin@harmonyschool.com")
print(f"Password: admin123")
print(f"\nYou can now login to your application!")
