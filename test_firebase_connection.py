"""
Quick test to verify Firebase connection
Run: python test_firebase_connection.py
"""

import firebase_admin
from firebase_admin import credentials, firestore
import os

try:
    # Check if credentials file exists
    cred_path = 'firebase-credentials.json'
    if not os.path.exists(cred_path):
        print("❌ ERROR: firebase-credentials.json not found!")
        print("Please download it from Firebase Console and place it in project root.")
        exit(1)
    
    print("✓ Found firebase-credentials.json")
    
    # Initialize Firebase
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    print("✓ Firebase initialized successfully")
    
    # Test Firestore connection
    db = firestore.client()
    print("✓ Connected to Firestore")
    
    # Try to write a test document
    test_ref = db.collection('_test').document('connection_test')
    test_ref.set({
        'status': 'connected',
        'message': 'Firebase is working!'
    })
    print("✓ Successfully wrote test document")
    
    # Read it back
    doc = test_ref.get()
    if doc.exists:
        print(f"✓ Successfully read test document: {doc.to_dict()}")
    
    # Clean up test document
    test_ref.delete()
    print("✓ Cleaned up test document")
    
    print("\n" + "="*50)
    print("🎉 SUCCESS! Firebase is connected and working!")
    print("="*50)
    print("\nNext step: Run the data migration script")
    print("Command: python migrate_data.py")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure firebase-credentials.json is in the project root")
    print("2. Make sure you ran: pip install firebase-admin")
    print("3. Check that the credentials file is valid JSON")
