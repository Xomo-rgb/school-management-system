import firebase_admin
from firebase_admin import credentials, firestore
from flask import g
from config import Config
import os

# Initialize Firebase Admin SDK
def init_firebase():
    if not firebase_admin._apps:
        cred_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

def get_firestore_db():
    """Get Firestore database instance"""
    if 'firestore_db' not in g:
        init_firebase()
        g.firestore_db = firestore.client()
    return g.firestore_db

def close_db(e=None):
    """Clean up database connection"""
    g.pop('firestore_db', None)

# Helper function to get school_id from session
def get_school_id():
    """Get current school ID from session or config"""
    from flask import session
    # For now, use default school. Later add multi-tenancy
    return session.get('school_id', Config.DEFAULT_SCHOOL_ID or 'default_school')
