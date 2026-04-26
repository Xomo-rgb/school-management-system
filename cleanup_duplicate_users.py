import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
school_id = 'harmony-school'
users_ref = db.collection('schools').document(school_id).collection('users')

# Get all users
all_users = users_ref.stream()
email_map = {}

for user_doc in all_users:
    user_data = user_doc.to_dict()
    email = user_data.get('email')
    
    if email in email_map:
        # Duplicate found - keep the older one, delete the newer
        print(f"Duplicate found for email: {email}")
        print(f"  Keeping: {email_map[email]['id']} - {email_map[email]['name']}")
        print(f"  Deleting: {user_doc.id} - {user_data.get('full_name')}")
        users_ref.document(user_doc.id).delete()
    else:
        email_map[email] = {
            'id': user_doc.id,
            'name': user_data.get('full_name')
        }

print("\nCleanup complete!")
print(f"Total unique users: {len(email_map)}")
