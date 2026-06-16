from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from firebase_db import get_firestore_db, get_school_id
from firebase_helpers import *
from utils import role_required, log_activity
from werkzeug.security import generate_password_hash

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
@role_required('school_admin')
def view_users():
    users = get_all_documents('users')
    users.sort(key=lambda x: x.get('full_name', ''))
    return render_template('view_users.html', users=users)

@user_bp.route('/add', methods=['GET', 'POST'])
@role_required('school_admin')
def add_user():
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        role = request.form.get('role')
        phone = request.form.get('phone', '').strip()

        if not all([full_name, email, role]):
            error = "Full Name, Email, and Role are required fields."
            if is_ajax:
                return jsonify({'success': False, 'error': error})
            flash(error, "error")
            return render_template('add_user.html', form_data=request.form)

        if role == 'teacher' and not phone:
            error = "Phone number is required for the 'Teacher' role."
            if is_ajax:
                return jsonify({'success': False, 'error': error})
            flash(error, "error")
            return render_template('add_user.html', form_data=request.form)

        existing_users = get_documents_where('users', 'email', '==', email)
        if existing_users:
            error = "A user with this email address already exists."
            if is_ajax:
                return jsonify({'success': False, 'error': error})
            flash(error, "error")
            return render_template('add_user.html', form_data=request.form)

        hashed_password = generate_password_hash("password123")
        user_data = {
            'full_name': full_name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'must_reset_password': True
        }
        if role == 'teacher' and phone:
            user_data['phone'] = phone

        add_document('users', user_data)
        log_activity(f"Created new user: '{full_name}' with role '{role}'.")
        flash(f"User '{full_name}' created successfully.", "success")

        if is_ajax:
            return jsonify({'success': True})
        return redirect(url_for('user.view_users'))

    return render_template('add_user.html')

@user_bp.route('/edit/<user_id>', methods=['GET', 'POST'])
@role_required('school_admin')
def edit_user(user_id):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        action = request.form.get('action')

        if action == 'update_details':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            role = request.form.get('role')
            phone = request.form.get('phone', '').strip()

            if role == 'teacher' and not phone:
                error = "Phone number is required for the 'Teacher' role."
                if is_ajax:
                    return jsonify({'success': False, 'error': error})
                flash(error, "error")
                return redirect(url_for('user.edit_user', user_id=user_id))

            user_data = {'full_name': full_name, 'email': email, 'role': role}
            if role == 'teacher' and phone:
                user_data['phone'] = phone

            update_document('users', user_id, user_data)
            log_activity(f"Edited user details for '{full_name}' (ID: {user_id}).")
            flash("User details updated successfully.", "success")

            if is_ajax:
                return jsonify({'success': True})

        elif action == 'reset_password':
            hashed_password = generate_password_hash("password123")
            update_document('users', user_id, {
                'password': hashed_password,
                'must_reset_password': True
            })
            log_activity(f"Reset password for user ID: {user_id}.")
            flash("Password reset to 'password123'. User will be prompted to change it on next login.", "success")

            if is_ajax:
                return jsonify({'success': True})

        return redirect(url_for('user.edit_user', user_id=user_id))

    user_data = get_document_by_id('users', user_id)
    if not user_data:
        flash("User not found.", "error")
        return redirect(url_for('user.view_users'))
        
    return render_template('edit_user.html', user=user_data)

@user_bp.route('/delete/<user_id>', methods=['POST'])
@role_required('school_admin')
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('user.view_users'))
    
    user_to_delete = get_document_by_id('users', user_id)
    user_name = user_to_delete.get('full_name', 'Unknown') if user_to_delete else 'Unknown'
    
    delete_document('users', user_id)
    log_activity(f"Deleted user: '{user_name}' (ID: {user_id}).")
    flash("User deleted successfully.", "success")
    return redirect(url_for('user.view_users'))

@user_bp.route('/assign_teacher/<user_id>', methods=['GET', 'POST'])
@role_required('school_admin')
def assign_teacher(user_id):
    from academic_helpers import get_subjects_for_class

    teacher = get_document_by_id('users', user_id)
    if not teacher or teacher.get('role') != 'teacher':
        flash("Teacher not found.", "error")
        return redirect(url_for('user.view_users'))

    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']

    if request.method == 'POST':
        assignments = []
        for class_name in CLASS_ORDER:
            key = class_name.replace(' ', '_')
            if request.form.get(f'class_{key}'):
                selected_subjects = request.form.getlist(f'subjects_{key}')
                assignments.append({
                    'class_name': class_name,
                    'subjects': selected_subjects
                })

        update_document('users', user_id, {'assignments': assignments})
        log_activity(f"Updated class assignments for teacher '{teacher.get('full_name')}'.")
        flash("Class assignments updated successfully.", "success")
        return redirect(url_for('user.assign_teacher', user_id=user_id))

    # Build class data with subjects from Firebase
    current_assignments = {a['class_name']: a['subjects'] for a in teacher.get('assignments', [])}
    classes_data = []
    for class_name in CLASS_ORDER:
        classes_data.append({
            'name': class_name,
            'subjects': get_subjects_for_class(class_name),
            'assigned': class_name in current_assignments,
            'assigned_subjects': current_assignments.get(class_name, [])
        })

    return render_template('assign_teacher.html', teacher=teacher, classes_data=classes_data)
