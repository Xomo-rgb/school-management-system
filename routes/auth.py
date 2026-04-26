from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from firebase_db import get_firestore_db, get_school_id
from werkzeug.security import check_password_hash
from utils import log_activity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        session.clear()

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return redirect(url_for('auth.login'))

        db = get_firestore_db()
        school_id = get_school_id()
        
        users_ref = db.collection('schools').document(school_id).collection('users')
        query = users_ref.where('email', '==', email).limit(1).stream()
        
        user_doc = None
        for doc in query:
            user_doc = doc
            break
        
        if user_doc:
            user = user_doc.to_dict()
            user['user_id'] = user_doc.id
            
            if check_password_hash(user['password'], password):
                log_activity(f"User logged in successfully.", user_id=user['user_id'], user_full_name=user['full_name'])

                session['user_id'] = user['user_id']
                session['full_name'] = user['full_name']
                session['email'] = user['email']
                session['role'] = user['role']
                session['school_id'] = school_id

                if user.get('must_reset_password'):
                    session['must_reset_password'] = True
                    return redirect(url_for('profile.force_password_reset'))

                user_role = user['role']
                if user_role == 'school_admin':
                    return redirect(url_for('admin.school_admin_dashboard'))
                elif user_role == 'teacher':
                    return redirect(url_for('teacher.teacher_dashboard'))
                elif user_role == 'accounts':
                    return redirect(url_for('admin.accounts_dashboard'))
                else:
                    flash("Your user role is undefined. Please contact an administrator.", "error")
                    return redirect(url_for('auth.login'))
            else:
                log_activity(f"Failed login attempt for email: '{email}'.")
                flash("Invalid email or password. Please try again.", "error")
                return redirect(url_for('auth.login'))
        else:
            log_activity(f"Failed login attempt for email: '{email}'.")
            flash("Invalid email or password. Please try again.", "error")
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    if 'full_name' in session:
        log_activity(f"User '{session['full_name']}' logged out.")

    session.clear()
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('auth.login'))