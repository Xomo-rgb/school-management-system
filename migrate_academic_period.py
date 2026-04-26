import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
school_id = 'harmony-school'

# Add initial active period to new collection
periods_ref = db.collection('schools').document(school_id).collection('academic_periods')

# Check if any period already exists
existing = list(periods_ref.stream())
if existing:
    print("Academic periods already exist:")
    for doc in existing:
        print(f"  - {doc.to_dict()}")
else:
    periods_ref.add({
        'year': '2024-2025',
        'term': 'Term 1',
        'status': 'active',
        'started_at': datetime.now(),
        'closed_at': None
    })
    print("Migrated: Created active period 2024-2025 - Term 1")
