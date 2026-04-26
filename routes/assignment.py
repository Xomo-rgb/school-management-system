from flask import Blueprint, render_template, flash, redirect, url_for
from utils import role_required

assignment_bp = Blueprint('assignment', __name__)

@assignment_bp.route('/manage/<teacher_user_id>')
@role_required('system_admin', 'school_admin')
def manage(teacher_user_id):
    flash("Assignments feature coming soon with Firebase", "info")
    return redirect(url_for('user.view_users'))
