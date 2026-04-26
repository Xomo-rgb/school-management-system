from flask import Blueprint, render_template, session
from firebase_db import get_firestore_db, get_school_id
from utils import role_required

temp_dashboard_bp = Blueprint('temp_dashboard', __name__)

@temp_dashboard_bp.route('/dashboard')
@role_required('system_admin', 'school_admin', 'teacher', 'accounts')
def dashboard():
    db = get_firestore_db()
    school_id = get_school_id()
    
    # Count students
    students = list(db.collection('schools').document(school_id).collection('students').stream())
    total_students = len(students)
    
    # Count users
    users = list(db.collection('schools').document(school_id).collection('users').stream())
    total_users = len(users)
    total_teachers = len([u for u in users if u.to_dict().get('role') == 'teacher'])
    
    # Get recent activity logs
    logs_ref = db.collection('schools').document(school_id).collection('activity_logs')
    recent_activities = logs_ref.order_by('timestamp', direction='DESCENDING').limit(5).stream()
    logs = [{'user': log.to_dict().get('user_full_name'), 
             'action': log.to_dict().get('action'),
             'timestamp': log.to_dict().get('timestamp')} 
            for log in recent_activities]
    
    return render_template('temp_dashboard.html',
                         user_name=session.get('full_name'),
                         user_role=session.get('role'),
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_users=total_users,
                         recent_activities=logs)
