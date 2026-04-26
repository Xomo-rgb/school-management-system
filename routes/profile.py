from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from firebase_helpers import *
from utils import role_required
from werkzeug.security import check_password_hash, generate_password_hash

profile_bp = Blueprint('profile', __name__)

def is_password_strong(password):
    if not password or len(password) < 8:
        return False
    return any(char.isdigit() for char in password)

@profile_bp.route('/settings', methods=['GET', 'POST'])
@role_required('school_admin', 'teacher', 'accounts')
def settings():
    user_id = session.get('user_id')
    user = get_document_by_id('users', user_id)

    if user and user.get('must_reset_password'):
        return redirect(url_for('profile.force_password_reset'))

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            
            if not full_name or not email:
                flash("Please fill out all fields.", "error")
                return redirect(url_for('profile.settings'))
            
            update_document('users', user_id, {'full_name': full_name, 'email': email})
            session['full_name'] = full_name
            session['email'] = email
            flash("Profile updated successfully.", "success")
            return redirect(url_for('profile.settings'))
        
        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_password or not new_password or not confirm_password:
                flash("Please complete all password fields.", "error")
                return redirect(url_for('profile.settings'))

            if new_password != confirm_password:
                flash("Passwords do not match.", "error")
                return redirect(url_for('profile.settings'))

            if not is_password_strong(new_password):
                flash("Password must be at least 8 characters and include at least one number.", "error")
                return redirect(url_for('profile.settings'))

            if not check_password_hash(user.get('password', ''), current_password):
                flash("Current password is incorrect.", "error")
                return redirect(url_for('profile.settings'))

            hashed_password = generate_password_hash(new_password)
            update_document('users', user_id, {'password': hashed_password, 'must_reset_password': False})
            flash("Password changed successfully.", "success")
            return redirect(url_for('profile.settings'))
    
    # Render appropriate template based on role
    if session.get('role') == 'teacher':
        return render_template('teacher_settings.html', user_data=user)
    elif session.get('role') == 'accounts':
        return render_template('accounts_settings.html', user_data=user)
    else:
        return render_template('settings.html', user_data=user)

@profile_bp.route('/force_password_reset', methods=['GET', 'POST'])
@role_required('school_admin', 'teacher', 'accounts')
def force_password_reset():
    user_id = session.get('user_id')
    user = get_document_by_id('users', user_id)

    if not user:
        flash("User session expired, please login again.", "error")
        return redirect(url_for('auth.login'))

    if not user.get('must_reset_password'):
        flash("Password already updated. You can continue to your dashboard.", "success")
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash("Please fill out all password fields.", "error")
            return redirect(url_for('profile.force_password_reset'))

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('profile.force_password_reset'))

        if not is_password_strong(new_password):
            flash("Password must be at least 8 characters and include at least one number.", "error")
            return redirect(url_for('profile.force_password_reset'))

        hashed_password = generate_password_hash(new_password)
        update_document('users', user_id, {'password': hashed_password, 'must_reset_password': False})
        flash("Your password has been updated successfully.", "success")

        role = session.get('role')
        if role == 'school_admin':
            return redirect(url_for('admin.school_admin_dashboard'))
        elif role == 'teacher':
            return redirect(url_for('teacher.teacher_dashboard'))
        elif role == 'accounts':
            return redirect(url_for('admin.accounts_dashboard'))

        return redirect(url_for('auth.login'))

    return render_template('force_password_change.html', user_data=user)
