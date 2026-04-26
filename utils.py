from functools import wraps
from flask import session, flash, redirect, url_for
from firebase_db import get_firestore_db, get_school_id
from datetime import datetime

# This decorator is unchanged
def role_required(*roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'role' not in session or session['role'] not in roles:
                flash("You do not have permission to access this page.", "error")
                return redirect(url_for('admin.unauthorized'))
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

def log_activity(action_description, user_id=None, user_full_name=None):
    """
    Records an activity in Firestore.
    """
    try:
        if user_id is None and 'user_id' in session:
            user_id = session['user_id']
        
        if user_full_name is None and 'full_name' in session:
            user_full_name = session['full_name']
            
        if user_full_name is None:
            user_full_name = "System/Unknown"

        db = get_firestore_db()
        school_id = get_school_id()
        
        db.collection('schools').document(school_id).collection('activity_logs').add({
            'user_id': user_id,
            'user_full_name': user_full_name,
            'action': action_description,
            'timestamp': datetime.utcnow()
        })
    except Exception as e:
        print(f"Error logging activity: {e}")