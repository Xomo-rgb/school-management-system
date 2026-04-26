from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from firebase_db import get_firestore_db, get_school_id
from firebase_helpers import *
from utils import role_required, log_activity
from datetime import datetime
from academic_helpers import get_current_academic_period, start_new_period, end_current_period, get_period_history, get_fee_structure, set_fee_structure, get_all_subjects, get_subjects_for_class, save_subjects_for_class
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO, StringIO
import csv

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/school_admin_dashboard')
@role_required('school_admin')
def school_admin_dashboard():
    total_students = count_documents('students')
    total_teachers = count_documents_where('users', 'role', '==', 'teacher')
    total_users = count_documents('users')
    return render_template('system_admin_dashboard.html',
                         total_students=total_students,
                         total_teachers=total_teachers,
                         total_users=total_users)

@admin_bp.route('/accounts_dashboard')
@role_required('accounts')
def accounts_dashboard():
    from academic_helpers import get_current_academic_period, get_fee_structure, calculate_student_balance
    
    current_period = get_current_academic_period()
    year = current_period['year']
    term = current_period['term']
    
    all_students = get_all_documents('students')
    total_students = len(all_students)
    
    # Get payments for the current period; if no active period exists, show all payments
    if year == 'Not Set' or term == 'Not Set':
        all_payments = get_all_documents('fee_payments')
    else:
        all_payments = get_documents_by_filters('fee_payments', [
            ('academic_year', '==', year),
            ('term', '==', term)
        ])
    payment_count = len(all_payments)
    total_collected = sum(p.get('amount_paid', 0) for p in all_payments)
    
    fee_structure = get_fee_structure(year, term) if year != 'Not Set' and term != 'Not Set' else {}
    total_expected = sum(fee_structure.get(s.get('class_name', ''), 0) for s in all_students)
    
    total_outstanding = total_expected - total_collected
    collection_rate = round((total_collected / total_expected * 100), 1) if total_expected > 0 else 0
    
    student_balances = []
    payments_by_student = {}
    for payment in all_payments:
        sid = payment.get('student_id')
        payments_by_student.setdefault(sid, []).append(payment)

    for student in all_students:
        expected = fee_structure.get(student.get('class_name', ''), 0)
        paid = sum(p.get('amount_paid', 0) for p in payments_by_student.get(student.get('id'), []))
        balance = expected - paid
        student_balances.append({
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'class_name': student.get('class_name', ''),
            'expected': expected,
            'paid': paid,
            'balance': balance
        })
    
    student_balances.sort(key=lambda x: x['balance'], reverse=True)
    
    recent_payments = sorted(all_payments, key=lambda x: x.get('payment_date', ''), reverse=True)[:5]
    students_dict = {s['id']: s for s in all_students}
    for p in recent_payments:
        student = students_dict.get(p.get('student_id'), {})
        p['student_name'] = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
        p['class_name'] = student.get('class_name', '')
        if p.get('payment_date') and hasattr(p['payment_date'], 'strftime'):
            p['payment_date'] = p['payment_date'].strftime('%d %b %Y')
    
    return render_template('accounts_dashboard.html',
                         current_period=current_period,
                         total_students=total_students,
                         payment_count=payment_count,
                         total_collected=total_collected,
                         total_expected=total_expected,
                         total_outstanding=total_outstanding,
                         collection_rate=collection_rate,
                         student_balances=student_balances,
                         recent_payments=recent_payments,
                         fee_structure_set=bool(fee_structure))

@admin_bp.route('/view_logs')
@role_required('school_admin')
def view_logs():
    db = get_firestore_db()
    school_id = get_school_id()
    logs_ref = db.collection('schools').document(school_id).collection('activity_logs')
    all_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(100).stream()
    logs = [{'user_full_name': log.to_dict().get('user_full_name'), 
             'action': log.to_dict().get('action'),
             'timestamp': log.to_dict().get('timestamp')} 
            for log in all_logs]
    return render_template('view_logs.html', logs=logs)

@admin_bp.route('/logs/pdf')
@role_required('school_admin')
def logs_pdf():
    db = get_firestore_db()
    school_id = get_school_id()
    logs_ref = db.collection('schools').document(school_id).collection('activity_logs')
    all_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(500).stream()
    logs = [{'user_full_name': log.to_dict().get('user_full_name'), 
             'action': log.to_dict().get('action'),
             'timestamp': log.to_dict().get('timestamp')} 
            for log in all_logs]
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph("System Activity Logs Report", title_style))
    story.append(Spacer(1, 12))
    
    if logs:
        log_data = [["Timestamp", "User", "Action"]]
        for log in logs:
            timestamp_str = log['timestamp'].strftime('%d-%b-%Y %H:%M:%S') if log.get('timestamp') and hasattr(log['timestamp'], 'strftime') else 'Unknown'
            log_data.append([
                timestamp_str,
                log.get('user_full_name', 'Unknown'),
                log.get('action', ''),
            ])
        log_table = Table(log_data, colWidths=[120, 120, 250])
        log_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("No logs found.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename=system_logs.pdf'
    return response

@admin_bp.route('/logs/csv')
@role_required('school_admin')
def logs_csv():
    db = get_firestore_db()
    school_id = get_school_id()
    logs_ref = db.collection('schools').document(school_id).collection('activity_logs')
    all_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(500).stream()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'User', 'Action'])
    for log in all_logs:
        log_data = log.to_dict()
        timestamp = log_data.get('timestamp')
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp and hasattr(timestamp, 'strftime') else 'Unknown'
        writer.writerow([timestamp_str, log_data.get('user_full_name', 'Unknown'), log_data.get('action', '')])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=system_logs.csv'
    return response

@admin_bp.route('/fee_payment_form')
@role_required('accounts')
def fee_payment_form():
    current_period = get_current_academic_period()
    return render_template('record_payment.html', current_period=current_period)

@admin_bp.route('/search_students')
@role_required('accounts')
def search_students():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    students = get_all_documents('students')
    matches = []
    for student in students:
        student_number = str(student.get('student_number', '')).lower()
        first_name = str(student.get('first_name', '')).lower()
        last_name = str(student.get('last_name', '')).lower()
        full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip().lower()

        if query in student_number or query in first_name or query in last_name or query in full_name:
            matches.append({
                'id': student.get('id'),
                'student_number': student.get('student_number', ''),
                'full_name': full_name.title(),
                'class_name': student.get('class_name', '')
            })
        if len(matches) >= 15:
            break

    return jsonify(matches)

@admin_bp.route('/submit_fee', methods=['POST'])
@role_required('accounts')
def submit_fee():
    student_identifier = request.form.get('student_identifier', '').strip()
    amount_paid = request.form.get('amount_paid')
    payment_date = request.form.get('payment_date')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    
    if not all([student_identifier, amount_paid, payment_date, term, academic_year]):
        flash("Please fill out all fields.", "error")
        return redirect(url_for('admin.fee_payment_form'))
    
    try:
        amount_paid = float(amount_paid)
    except ValueError:
        flash("Invalid amount entered. Please use numbers only.", "error")
        return redirect(url_for('admin.fee_payment_form'))
    
    students = []
    # support suggestions formatted as "STUDENT_NUMBER - Full Name"
    if ' - ' in student_identifier:
        identifier_left = student_identifier.split(' - ')[0].strip()
        if identifier_left:
            student_identifier = identifier_left

    name_parts = student_identifier.split()
    if student_identifier.startswith('HS-'):
        students = get_documents_where('students', 'student_number', '==', student_identifier)

    if not students:
        # try exact full name match (case-insensitive fallback)
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
            students = get_documents_by_filters('students', [
                ('first_name', '==', first_name),
                ('last_name', '==', last_name)
            ])

    if not students and len(name_parts) == 1:
        students = get_documents_where('students', 'first_name', '==', student_identifier)
        if not students:
            students = get_documents_where('students', 'last_name', '==', student_identifier)

    if not students:
        # fallback to case-insensitive exact match across all students
        all_students = get_all_documents('students')
        normalized_input = student_identifier.lower()
        for student in all_students:
            full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip().lower()
            student_number = str(student.get('student_number', '')).strip().lower()
            if normalized_input == full_name or normalized_input == student_number:
                students = [student]
                break

    if not students:
        flash("Student not found. Use student number or exact student name.", "error")
        return redirect(url_for('admin.fee_payment_form'))
    if len(students) > 1:
        flash("Multiple students matched that name. Please use the student number.", "error")
        return redirect(url_for('admin.fee_payment_form'))
    
    student = students[0]
    student_name = f"{student['first_name']} {student.get('last_name', '')}".strip()
    
    payment_data = {
        'student_id': student['id'],
        'amount_paid': amount_paid,
        'payment_date': datetime.strptime(payment_date, '%Y-%m-%d'),
        'term': term,
        'academic_year': academic_year
    }
    
    add_document('fee_payments', payment_data)
    log_activity(f"Recorded fee payment of {amount_paid} for student '{student_name}' ({student.get('student_number', '')}).")
    flash("Fee payment recorded successfully.", "success")
    return redirect(url_for('admin.fee_payment_form'))

@admin_bp.route('/view_fee_payments')
@role_required('school_admin', 'accounts')
def view_fee_payments():
    all_payments = get_all_documents('fee_payments')
    academic_years = sorted(list(set([p.get('academic_year') for p in all_payments if p.get('academic_year')])), reverse=True)
    terms = sorted(list(set([p.get('term') for p in all_payments if p.get('term')])))
    
    all_students = get_all_documents('students')
    classes = sorted(list(set([s.get('class_name') for s in all_students if s.get('class_name')])))
    
    return render_template('view_fee_payments.html', 
                         academic_years=academic_years, 
                         terms=terms, 
                         classes=classes)

@admin_bp.route('/filter_fee_payments', methods=['POST'])
@role_required('school_admin', 'accounts')
def filter_fee_payments():
    selected_year = request.form.get('academic_year')
    selected_term = request.form.get('term')
    selected_class = request.form.get('class_name')
    
    filters = []
    if selected_year:
        filters.append(('academic_year', '==', selected_year))
    if selected_term:
        filters.append(('term', '==', selected_term))

    if filters:
        payments = get_documents_by_filters('fee_payments', filters)
    else:
        payments = get_all_documents('fee_payments')

    if selected_class:
        students = get_documents_where('students', 'class_name', '==', selected_class)
    else:
        students = get_all_documents('students')

    students_dict = {s['id']: s for s in students}
    
    filtered_payments = []
    for payment in payments:
        student = students_dict.get(payment.get('student_id'))
        if not student:
            continue
        
        payment_dict = dict(payment)
        payment_dict['student_number'] = student.get('student_number')
        payment_dict['first_name'] = student.get('first_name')
        payment_dict['middle_name'] = student.get('middle_name')
        payment_dict['last_name'] = student.get('last_name')
        payment_dict['class_name'] = student.get('class_name')
        payment_dict["full_name"] = f"{student.get('first_name', '')} {student.get('middle_name') or ''} {student.get('last_name', '')}".replace('  ', ' ')
        
        if payment_dict.get("payment_date"):
            payment_dict["payment_date"] = payment_dict["payment_date"].strftime("%Y-%m-%d") if hasattr(payment_dict["payment_date"], 'strftime') else payment_dict["payment_date"]
        
        filtered_payments.append(payment_dict)
    
    return jsonify({"payments": filtered_payments})

@admin_bp.route('/edit_fee/<payment_id>', methods=['GET', 'POST'])
@role_required('accounts')
def edit_fee(payment_id):
    if request.method == 'POST':
        amount_paid = request.form.get('amount_paid')
        payment_date = request.form.get('payment_date')
        term = request.form.get('term')
        academic_year = request.form.get('academic_year')
        
        if not all([amount_paid, payment_date, term, academic_year]):
            flash("Please fill out all fields.", "error")
            return redirect(url_for('admin.edit_fee', payment_id=payment_id))
        
        try:
            amount_paid = float(amount_paid)
        except ValueError:
            flash("Invalid amount entered.", "error")
            return redirect(url_for('admin.edit_fee', payment_id=payment_id))
        
        payment_data = {
            'amount_paid': amount_paid,
            'payment_date': datetime.strptime(payment_date, '%Y-%m-%d'),
            'term': term,
            'academic_year': academic_year
        }
        
        update_document('fee_payments', payment_id, payment_data)
        log_activity(f"Edited fee payment record (ID: {payment_id}).")
        flash("Fee payment updated successfully.", "success")
        return redirect(url_for('admin.view_fee_payments'))
    
    payment = get_document_by_id('fee_payments', payment_id)
    if not payment:
        flash("Fee payment record not found.", "error")
        return redirect(url_for('admin.view_fee_payments'))
    
    student = get_document_by_id('students', payment.get('student_id'))
    if student:
        payment['student_number'] = student.get('student_number')
        payment['first_name'] = student.get('first_name')
        payment['middle_name'] = student.get('middle_name')
        payment['last_name'] = student.get('last_name')
    
    if payment.get('payment_date'):
        payment['payment_date'] = payment['payment_date'].strftime('%Y-%m-%d') if hasattr(payment['payment_date'], 'strftime') else payment['payment_date']
    
    return render_template('edit_fee.html', payment=payment)

@admin_bp.route('/delete_fee/<payment_id>', methods=['POST'])
@role_required('accounts')
def delete_fee(payment_id):
    payment = get_document_by_id('fee_payments', payment_id)
    if not payment:
        flash("Payment record not found.", "error")
        return redirect(url_for('admin.view_fee_payments'))
    
    student = get_document_by_id('students', payment.get('student_id'))
    student_number = student.get('student_number') if student else 'Unknown'
    
    delete_document('fee_payments', payment_id)
    log_activity(f"Deleted fee payment record (ID: {payment_id}) for student {student_number}.")
    flash("Fee payment deleted successfully.", "success")
    return redirect(url_for('admin.view_fee_payments'))

@admin_bp.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403

@admin_bp.route('/get_students_per_class_data')
@role_required('school_admin')
def get_students_per_class_data():
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']
    
    all_students = get_all_documents('students')
    class_counts = {}
    for student in all_students:
        class_name = student.get('class_name', 'Unknown')
        class_counts[class_name] = class_counts.get(class_name, 0) + 1
    
    # Sort by CLASS_ORDER, put unknown classes at the end
    sorted_labels = [c for c in CLASS_ORDER if c in class_counts]
    sorted_data = [class_counts[c] for c in sorted_labels]
    
    return jsonify({'labels': sorted_labels, 'data': sorted_data})

@admin_bp.route('/get_users_by_role_data')
@role_required('school_admin')
def get_users_by_role_data():
    all_users = get_all_documents('users')
    role_counts = {}
    for user in all_users:
        role = user.get('role', 'Unknown')
        role_counts[role] = role_counts.get(role, 0) + 1
    
    return jsonify({
        'labels': list(role_counts.keys()),
        'data': list(role_counts.values())
    })

@admin_bp.route('/academic_settings')
@role_required('school_admin')
def academic_settings():
    current_period = get_current_academic_period()
    period_history = get_period_history()
    return render_template('academic_settings.html', current_period=current_period, period_history=period_history)

@admin_bp.route('/start_period', methods=['POST'])
@role_required('school_admin')
def start_period():
    current = get_current_academic_period()
    if current.get('status') == 'active':
        flash("Please end the current period before starting a new one.", "error")
        return redirect(url_for('admin.academic_settings'))

    year = request.form.get('academic_year', '').strip()
    term = request.form.get('term', '').strip()

    if not year or not term:
        flash("Please provide both academic year and term.", "error")
        return redirect(url_for('admin.academic_settings'))

    import re
    if not re.match(r'\d{4}-\d{4}', year):
        flash("Academic year format must be YYYY-YYYY (e.g. 2025-2026).", "error")
        return redirect(url_for('admin.academic_settings'))

    start_new_period(year, term)
    log_activity(f"Started new academic period: {year} - {term}")
    flash(f"Academic period {year} - {term} started successfully.", "success")
    return redirect(url_for('admin.academic_settings'))

@admin_bp.route('/end_period', methods=['POST'])
@role_required('school_admin')
def end_period():
    current = get_current_academic_period()
    if current.get('status') != 'active':
        flash("No active period to end.", "error")
        return redirect(url_for('admin.academic_settings'))

    end_current_period()
    log_activity(f"Ended academic period: {current.get('year')} - {current.get('term')}")
    flash(f"{current.get('year')} - {current.get('term')} has been closed. All data is now read-only.", "success")
    return redirect(url_for('admin.academic_settings'))

@admin_bp.route('/promote_students', methods=['GET', 'POST'])
@role_required('school_admin')
def promote_students():
    PASS_MARK = 40.0
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']

    if request.method == 'POST':
        promotions = request.form.getlist('promote')
        year = request.form.get('year')
        term = request.form.get('term')
        all_results = get_documents_by_filters('exam_results', [
            ('academic_year', '==', year),
            ('term', '==', term)
        ])
        from academic_helpers import get_subjects_for_class

        promoted = 0
        skipped = 0
        for student_id in promotions:
            student = get_document_by_id('students', student_id)
            if not student:
                continue

            class_name = student.get('class_name', '')
            required_subjects = get_subjects_for_class(class_name)

            student_results = [
                r for r in all_results
                if r.get('student_id') == student_id
            ]

            # Must have results for ALL subjects
            entered_subjects = set(r.get('subject') for r in student_results)
            if not required_subjects or not all(s in entered_subjects for s in required_subjects):
                skipped += 1
                continue

            scores = [r.get('final_score', 0) for r in student_results]
            average = sum(scores) / len(scores)
            if average < PASS_MARK:
                skipped += 1
                continue

            if class_name in CLASS_ORDER:
                idx = CLASS_ORDER.index(class_name)
                if idx < len(CLASS_ORDER) - 1:
                    update_document('students', student_id, {'class_name': CLASS_ORDER[idx + 1]})
                    promoted += 1

        log_activity(f"Promoted {promoted} students after {year} - {term}")
        msg = f"{promoted} student(s) promoted successfully."
        if skipped:
            msg += f" {skipped} skipped (incomplete results or below pass mark)."
        flash(msg, "success")
        return redirect(url_for('admin.promote_students'))

    # GET - calculate results
    current_period = get_current_academic_period()
    year = current_period.get('year')
    term = current_period.get('term')

    all_students = get_all_documents('students')
    all_results = get_documents_by_filters('exam_results', [
        ('academic_year', '==', year),
        ('term', '==', term)
    ])
    from academic_helpers import get_subjects_for_class

    student_data = []
    for student in all_students:
        sid = student.get('id')
        class_name = student.get('class_name', '')
        required_subjects = get_subjects_for_class(class_name)

        student_results = [
            r for r in all_results
            if r.get('student_id') == sid
        ]

        entered_subjects = set(r.get('subject') for r in student_results)
        missing_subjects = [s for s in required_subjects if s not in entered_subjects]
        all_entered = len(missing_subjects) == 0 and len(required_subjects) > 0

        if all_entered:
            scores = [r.get('final_score', 0) for r in student_results]
            average = round(sum(scores) / len(scores), 1)
            passed = average >= PASS_MARK
        else:
            average = None
            passed = None

        idx = CLASS_ORDER.index(class_name) if class_name in CLASS_ORDER else -1
        next_class = CLASS_ORDER[idx + 1] if 0 <= idx < len(CLASS_ORDER) - 1 else 'Graduated'

        student_data.append({
            'id': sid,
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'current_class': class_name,
            'next_class': next_class,
            'average': average,
            'passed': passed,
            'subjects_count': len(student_results),
            'required_count': len(required_subjects),
            'missing_subjects': missing_subjects
        })

    student_data.sort(key=lambda x: (x.get('current_class', ''), x.get('name', '')))

    return render_template('promote_students.html',
                         student_data=student_data,
                         current_period=current_period,
                         pass_mark=PASS_MARK)

@admin_bp.route('/view_all_results')
@role_required('school_admin')
def view_all_results():
    from academic_helpers import get_period_history
    current_period = get_current_academic_period()
    all_periods = get_period_history()
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']
    return render_template('admin_view_results.html',
                         current_period=current_period,
                         all_periods=all_periods,
                         classes=CLASS_ORDER)

@admin_bp.route('/get_admin_class_results', methods=['POST'])
@role_required('school_admin')
def get_admin_class_results():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject_filter = request.form.get('subject_filter', '')

    if not all([class_name, term, academic_year]):
        return jsonify([])

    students = get_documents_where('students', 'class_name', '==', class_name)
    all_results = get_documents_by_filters('exam_results', [
        ('term', '==', term),
        ('academic_year', '==', academic_year)
    ])

    results_data = []
    for student in students:
        sid = student['id']
        student_results = [r for r in all_results
                          if r.get('student_id') == sid]

        if subject_filter:
            student_results = [r for r in student_results if r.get('subject') == subject_filter]

        scores = [r.get('final_score', 0) for r in student_results]
        average = round(sum(scores) / len(scores), 1) if scores else None

        results_data.append({
            'student_id': sid,
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'subjects': [{'subject': r.get('subject'), 'score': r.get('final_score')} for r in student_results],
            'average': average,
            'passed': average >= 40 if average is not None else None
        })

    results_data.sort(key=lambda x: x['name'])
    return jsonify(results_data)

@admin_bp.route('/results/pdf', methods=['POST'])
@role_required('school_admin')
def results_pdf():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject_filter = request.form.get('subject_filter', '')

    if not all([class_name, term, academic_year]):
        flash("Please select class, term, and academic year.", "error")
        return redirect(url_for('admin.view_all_results'))

    students = get_documents_where('students', 'class_name', '==', class_name)
    all_results = get_documents_by_filters('exam_results', [
        ('term', '==', term),
        ('academic_year', '==', academic_year)
    ])

    results_data = []
    for student in students:
        sid = student['id']
        student_results = [r for r in all_results
                          if r.get('student_id') == sid]

        if subject_filter:
            student_results = [r for r in student_results if r.get('subject') == subject_filter]

        results_data.append({
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'subjects': [{'subject': r.get('subject'), 'score': r.get('final_score')} for r in student_results],
        })

    results_data.sort(key=lambda x: x['name'])
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph(f"Exam Results Report - {class_name.title()}", title_style))
    story.append(Paragraph(f"Term: {term} | Academic Year: {academic_year}", styles['Heading3']))
    if subject_filter:
        story.append(Paragraph(f"Subject: {subject_filter}", styles['Heading3']))
    story.append(Spacer(1, 12))
    
    if results_data:
        # Get all unique subjects
        all_subjects = set()
        for student in results_data:
            for subj in student['subjects']:
                all_subjects.add(subj['subject'])
        subjects_list = sorted(list(all_subjects))
        
        # Create table data
        table_data = [["Student Name", "Student Number"] + subjects_list]
        for student in results_data:
            row = [student['name'], student['student_number']]
            subject_scores = {subj['subject']: subj['score'] for subj in student['subjects']}
            for subj in subjects_list:
                row.append(subject_scores.get(subj, '-'))
            table_data.append(row)
        
        col_widths = [120, 100] + [60] * len(subjects_list)
        result_table = Table(table_data, colWidths=col_widths)
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(result_table)
    else:
        story.append(Paragraph("No results found for the selected criteria.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    filename = f"results_{class_name}_{term}_{academic_year}.pdf"
    if subject_filter:
        filename = f"results_{class_name}_{subject_filter}_{term}_{academic_year}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@admin_bp.route('/results/csv', methods=['POST'])
@role_required('school_admin')
def results_csv():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject_filter = request.form.get('subject_filter', '')

    if not all([class_name, term, academic_year]):
        flash("Please select class, term, and academic year.", "error")
        return redirect(url_for('admin.view_all_results'))

    students = get_documents_where('students', 'class_name', '==', class_name)
    all_results = get_documents_by_filters('exam_results', [
        ('term', '==', term),
        ('academic_year', '==', academic_year)
    ])

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student Number', 'Subject', 'Score'])
    for student in students:
        sid = student['id']
        student_results = [r for r in all_results if r.get('student_id') == sid]
        if subject_filter:
            student_results = [r for r in student_results if r.get('subject') == subject_filter]
        full_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
        for result in student_results:
            writer.writerow([full_name, student.get('student_number', ''), result.get('subject', ''), result.get('final_score', '')])

    filename = f"results_{class_name}_{term}_{academic_year}.csv"
    if subject_filter:
        filename = f"results_{class_name}_{subject_filter}_{term}_{academic_year}.csv"

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@admin_bp.route('/students/pdf')
@role_required('school_admin')
def students_pdf():
    all_students = get_all_documents('students')
    all_students.sort(key=lambda x: (x.get('class_name', ''), x.get('first_name', '')))
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph("Students List Report", title_style))
    story.append(Spacer(1, 12))
    
    if all_students:
        student_data = [["Name", "Student Number", "Class", "Guardian Name", "Guardian Phone"]]
        for student in all_students:
            student_data.append([
                f"{student.get('first_name', '')} {student.get('middle_name', '')} {student.get('last_name', '')}".strip(),
                student.get('student_number', ''),
                student.get('class_name', ''),
                student.get('guardian_name', ''),
                student.get('guardian_phone', ''),
            ])
        student_table = Table(student_data, colWidths=[120, 100, 80, 120, 100])
        student_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(student_table)
    else:
        story.append(Paragraph("No students found.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename=students_list.pdf'
    return response

@admin_bp.route('/students/csv')
@role_required('school_admin')
def students_csv():
    all_students = get_all_documents('students')
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Student Number', 'Class', 'Guardian Name', 'Guardian Phone'])
    for student in sorted(all_students, key=lambda x: (x.get('class_name', ''), x.get('first_name', ''))):
        writer.writerow([
            f"{student.get('first_name', '')} {student.get('middle_name', '')} {student.get('last_name', '')}".strip(),
            student.get('student_number', ''),
            student.get('class_name', ''),
            student.get('guardian_name', ''),
            student.get('guardian_phone', ''),
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=students_list.csv'
    return response

@admin_bp.route('/fee_payments/pdf', methods=['POST'])
@role_required('school_admin')
def fee_payments_pdf():
    selected_year = request.form.get('academic_year')
    selected_term = request.form.get('term')
    selected_class = request.form.get('class_name')
    
    filters = []
    if selected_year:
        filters.append(('academic_year', '==', selected_year))
    if selected_term:
        filters.append(('term', '==', selected_term))

    if filters:
        payments = get_documents_by_filters('fee_payments', filters)
    else:
        payments = get_all_documents('fee_payments')

    if selected_class:
        students = get_documents_where('students', 'class_name', '==', selected_class)
    else:
        students = get_all_documents('students')

    students_dict = {s['id']: s for s in students}
    
    filtered_payments = []
    for payment in payments:
        student = students_dict.get(payment.get('student_id'))
        if not student:
            continue
        
        payment_dict = dict(payment)
        payment_dict['student_number'] = student.get('student_number')
        payment_dict['first_name'] = student.get('first_name')
        payment_dict['middle_name'] = student.get('middle_name')
        payment_dict['last_name'] = student.get('last_name')
        payment_dict['class_name'] = student.get('class_name')
        payment_dict["full_name"] = f"{student.get('first_name', '')} {student.get('middle_name') or ''} {student.get('last_name', '')}".replace('  ', ' ')
        
        if payment_dict.get("payment_date"):
            payment_dict["payment_date"] = payment_dict["payment_date"].strftime("%Y-%m-%d") if hasattr(payment_dict["payment_date"], 'strftime') else payment_dict["payment_date"]
        
        filtered_payments.append(payment_dict)
    
    filtered_payments.sort(key=lambda x: x.get('payment_date', ''), reverse=True)
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph("Fee Payments Report", title_style))
    filters_desc = []
    if selected_year:
        filters_desc.append(f"Year: {selected_year}")
    if selected_term:
        filters_desc.append(f"Term: {selected_term}")
    if selected_class:
        filters_desc.append(f"Class: {selected_class}")
    if filters_desc:
        story.append(Paragraph(" | ".join(filters_desc), styles['Heading3']))
    story.append(Spacer(1, 12))
    
    if filtered_payments:
        payment_data = [["Date", "Student Name", "Student Number", "Class", "Amount", "Term", "Year"]]
        for payment in filtered_payments:
            payment_data.append([
                payment.get('payment_date', ''),
                payment.get('full_name', ''),
                payment.get('student_number', ''),
                payment.get('class_name', ''),
                f"{payment.get('amount_paid', 0):.2f}",
                payment.get('term', ''),
                payment.get('academic_year', ''),
            ])
        payment_table = Table(payment_data, colWidths=[80, 120, 100, 60, 60, 50, 60])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(payment_table)
    else:
        story.append(Paragraph("No payments found for the selected filters.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    filename = "fee_payments.pdf"
    if selected_year or selected_term or selected_class:
        parts = []
        if selected_year:
            parts.append(selected_year)
        if selected_term:
            parts.append(selected_term.replace(' ', ''))
        if selected_class:
            parts.append(selected_class.replace(' ', ''))
        filename = f"fee_payments_{'_'.join(parts)}.pdf"
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@admin_bp.route('/fee_payments/csv', methods=['POST'])
@role_required('school_admin')
def fee_payments_csv():
    selected_year = request.form.get('academic_year')
    selected_term = request.form.get('term')
    selected_class = request.form.get('class_name')
    
    filters = []
    if selected_year:
        filters.append(('academic_year', '==', selected_year))
    if selected_term:
        filters.append(('term', '==', selected_term))

    if filters:
        payments = get_documents_by_filters('fee_payments', filters)
    else:
        payments = get_all_documents('fee_payments')

    if selected_class:
        students = get_documents_where('students', 'class_name', '==', selected_class)
    else:
        students = get_all_documents('students')

    students_dict = {s['id']: s for s in students}

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Student Name', 'Student Number', 'Class', 'Amount Paid', 'Term', 'Academic Year'])
    for payment in payments:
        student = students_dict.get(payment.get('student_id'))
        if not student:
            continue
        full_name = f"{student.get('first_name', '')} {student.get('middle_name') or ''} {student.get('last_name', '')}".replace('  ', ' ').strip()
        date_str = payment.get('payment_date').strftime('%Y-%m-%d') if payment.get('payment_date') and hasattr(payment.get('payment_date'), 'strftime') else payment.get('payment_date') or ''
        writer.writerow([date_str, full_name, student.get('student_number', ''), student.get('class_name', ''), payment.get('amount_paid', 0), payment.get('term', ''), payment.get('academic_year', '')])

    filename = 'fee_payments.csv'
    if selected_year or selected_term or selected_class:
        parts = []
        if selected_year:
            parts.append(selected_year)
        if selected_term:
            parts.append(selected_term.replace(' ', ''))
        if selected_class:
            parts.append(selected_class.replace(' ', ''))
        filename = f"fee_payments_{'_'.join(parts)}.csv"

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@admin_bp.route('/manage_subjects', methods=['GET', 'POST'])
@role_required('school_admin')
def manage_subjects():
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']

    if request.method == 'POST':
        action = request.form.get('action')
        class_name = request.form.get('class_name')
        current_subjects = get_subjects_for_class(class_name)

        if action == 'add_subject':
            new_subject = request.form.get('new_subject', '').strip()
            if new_subject and new_subject not in current_subjects:
                current_subjects.append(new_subject)
                save_subjects_for_class(class_name, current_subjects)
                log_activity(f"Added subject '{new_subject}' to {class_name}")
                flash(f"'{new_subject}' added to {class_name.title()}.", "success")
            else:
                flash("Subject already exists or name is empty.", "error")

        elif action == 'remove_subject':
            subject = request.form.get('subject')
            if subject in current_subjects:
                current_subjects.remove(subject)
                save_subjects_for_class(class_name, current_subjects)
                log_activity(f"Removed subject '{subject}' from {class_name}")
                flash(f"'{subject}' removed from {class_name.title()}.", "success")

        return redirect(url_for('admin.manage_subjects'))

    all_subjects = get_all_subjects()
    # Ensure all classes appear even if not in Firebase
    subjects_by_class = {c: all_subjects.get(c, []) for c in CLASS_ORDER}

    return render_template('manage_subjects.html', subjects_by_class=subjects_by_class, classes=CLASS_ORDER)

@admin_bp.route('/manage_fees', methods=['GET', 'POST'])
@role_required('school_admin')
def manage_fees():
    current_period = get_current_academic_period()

    if current_period.get('status') != 'active':
        flash("No active academic period. Please start a new period first.", "error")
        return redirect(url_for('admin.academic_settings'))

    year = current_period['year']
    term = current_period['term']

    if request.method == 'POST':
        all_students = get_all_documents('students')
        classes = sorted(list(set([s.get('class_name') for s in all_students if s.get('class_name')])))

        fee_data = {}
        for class_name in classes:
            # Replace spaces with underscores for form field name lookup
            field_name = f'fee_{class_name.replace(" ", "_")}'
            fee_amount = request.form.get(field_name)
            if fee_amount:
                try:
                    fee_data[class_name] = float(fee_amount)
                except ValueError:
                    pass

        if fee_data:
            set_fee_structure(year, term, fee_data)
            log_activity(f"Updated fee structure for {year} - {term}")
            flash(f"Fee structure for {year} - {term} saved successfully.", "success")
        else:
            flash("Please enter at least one fee amount.", "error")

        return redirect(url_for('admin.manage_fees'))

    all_students = get_all_documents('students')
    classes = sorted(list(set([s.get('class_name') for s in all_students if s.get('class_name')])))
    current_fees = get_fee_structure(year, term)

    return render_template('manage_fees.html',
                         current_period=current_period,
                         classes=classes,
                         current_fees=current_fees)
