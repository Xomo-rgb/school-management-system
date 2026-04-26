import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
school_id = 'harmony-school'
users_ref = db.collection('schools').document(school_id).collection('users')

# Update all system_admin users to school_admin
updated = 0
for doc in users_ref.stream():
    data = doc.to_dict()
    if data.get('role') == 'system_admin':
        users_ref.document(doc.id).update({'role': 'school_admin'})
        print(f"Updated: {data.get('full_name')} -> school_admin")
        updated += 1

print(f"\nDone! Updated {updated} user(s).")
