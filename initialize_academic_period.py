import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
school_id = 'harmony-school'

# Set initial academic period
settings_ref = db.collection('schools').document(school_id).collection('settings').document('academic_period')
settings_ref.set({
    'current_year': '2024-2025',
    'current_term': 'Term 1'
})

print("Academic period initialized successfully!")
print("Current Year: 2024-2025")
print("Current Term: Term 1")
print("\nYou can change this in the admin dashboard under 'Academic Settings'")
