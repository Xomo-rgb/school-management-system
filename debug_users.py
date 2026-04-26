"""
Debug script to check Firebase users
"""

import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase-credentials.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

school_id = input("Enter school ID (default: harmony-school): ").strip() or "harmony-school"

print(f"\nChecking users in school: {school_id}")
print("="*50)

users_ref = db.collection('schools').document(school_id).collection('users')
users = users_ref.stream()

count = 0
for user in users:
    count += 1
    user_data = user.to_dict()
    print(f"\nUser {count}:")
    print(f"  ID: {user.id}")
    print(f"  Email: {user_data.get('email')}")
    print(f"  Name: {user_data.get('full_name')}")
    print(f"  Role: {user_data.get('role')}")
    print(f"  Password Hash: {user_data.get('password')[:50]}...")

if count == 0:
    print("\n❌ No users found!")
    print("Run: python create_admin_user.py")
else:
    print(f"\n✓ Found {count} user(s)")
