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
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']

    current_period = get_current_academic_period()
    year = current_period['year']
    term = current_period['term']

    all_students = get_all_documents('students')
    total_students = len(all_students)
    students_dict = {s['id']: s for s in all_students}

    if year == 'Not Set' or term == 'Not Set':
        all_payments = get_all_documents('fee_payments')
    else:
        all_payments = get_documents_by_filters('fee_payments', [
            ('academic_year', '==', year),
            ('term', '==', term)
        ])

    total_collected = sum(p.get('amount_paid', 0) for p in all_payments)
    fee_structure = get_fee_structure(year, term) if year != 'Not Set' and term != 'Not Set' else {}
    total_expected = sum(fee_structure.get(s.get('class_name', ''), 0) for s in all_students)
    total_outstanding = max(0, total_expected - total_collected)
    collection_rate = round((total_collected / total_expected * 100), 1) if total_expected > 0 else 0

    # Pre-compute total paid per student for balance calculation
    student_total_paid = {}
    for p in all_payments:
        sid = p.get('student_id')
        student_total_paid[sid] = student_total_paid.get(sid, 0) + p.get('amount_paid', 0)

    recent_payments = sorted(all_payments, key=lambda x: x.get('payment_date', ''), reverse=True)[:8]
    for p in recent_payments:
        student = students_dict.get(p.get('student_id'), {})
        p['student_name'] = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
        p['class_name'] = student.get('class_name', '')
        if p.get('payment_date') and hasattr(p['payment_date'], 'strftime'):
            p['payment_date'] = p['payment_date'].strftime('%d %b %Y')
        sid = p.get('student_id')
        expected = fee_structure.get(student.get('class_name', ''), 0)
        total_paid = student_total_paid.get(sid, 0)
        p['balance'] = expected - total_paid

    collection_by_class = []
    if fee_structure:
        class_student_counts = {}
        for s in all_students:
            cn = s.get('class_name', '')
            class_student_counts[cn] = class_student_counts.get(cn, 0) + 1

        class_payments = {}
        for p in all_payments:
            cn = students_dict.get(p.get('student_id'), {}).get('class_name', '')
            class_payments[cn] = class_payments.get(cn, 0) + p.get('amount_paid', 0)

        for cn, fee_amount in fee_structure.items():
            if fee_amount == 0:
                continue
            count = class_student_counts.get(cn, 0)
            expected = fee_amount * count
            collected = class_payments.get(cn, 0)
            rate = round(collected / expected * 100) if expected > 0 else 0
            collection_by_class.append({
                'class_name': cn,
                'students': count,
                'expected': expected,
                'collected': collected,
                'outstanding': max(0, expected - collected),
                'rate': rate
            })

        collection_by_class.sort(
            key=lambda x: CLASS_ORDER.index(x['class_name']) if x['class_name'] in CLASS_ORDER else 99
        )

    return render_template('accounts_dashboard.html',
                         current_period=current_period,
                         total_students=total_students,
                         total_collected=total_collected,
                         total_expected=total_expected,
                         total_outstanding=total_outstanding,
                         collection_rate=collection_rate,
                         recent_payments=recent_payments,
                         collection_by_class=collection_by_class,
                         fee_structure_set=bool(fee_structure))

@admin_bp.route('/student_balances')
@role_required('school_admin', 'accounts')
def student_balances():
    current_period = get_current_academic_period()
    all_periods = get_period_history()

    selected_year = request.args.get('year', current_period.get('year', ''))
    selected_term = request.args.get('term', current_period.get('term', ''))
    is_current = (selected_year == current_period.get('year') and
                  selected_term == current_period.get('term'))

    all_students = get_all_documents('students')
    all_students.sort(key=lambda x: (x.get('class_name', ''), x.get('last_name', ''), x.get('first_name', '')))

    all_payments = get_all_documents('fee_payments')
    payments_map = {}
    for p in all_payments:
        key = (p.get('student_id'), p.get('academic_year'), p.get('term'))
        payments_map[key] = payments_map.get(key, 0) + p.get('amount_paid', 0)

    closed_periods = [(p.get('year'), p.get('term')) for p in all_periods if p.get('status') == 'closed']
    fee_structures = {}
    if is_current and closed_periods:
        for p_year, p_term in closed_periods:
            fee_structures[(p_year, p_term)] = get_fee_structure(p_year, p_term)

    has_period = selected_year and selected_year != 'Not Set' and selected_term and selected_term != 'Not Set'
    selected_fee_structure = get_fee_structure(selected_year, selected_term) if has_period else {}

    balances = []
    for student in all_students:
        sid = student['id']
        class_name = student.get('class_name', '')
        expected = selected_fee_structure.get(class_name, 0)
        paid = payments_map.get((sid, selected_year, selected_term), 0)

        credit = 0
        if is_current:
            for p_year, p_term in closed_periods:
                prev_fee = fee_structures.get((p_year, p_term), {}).get(class_name, 0)
                prev_paid = payments_map.get((sid, p_year, p_term), 0)
                if prev_paid > prev_fee:
                    credit += prev_paid - prev_fee

        balances.append({
            'student_number': student.get('student_number', ''),
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'class_name': class_name,
            'expected': expected,
            'paid': paid,
            'credit': credit,
            'balance': expected - paid - credit
        })

    balances.sort(key=lambda x: x['balance'], reverse=True)

    return render_template('student_balances.html',
                         balances=balances,
                         current_period=current_period,
                         all_periods=all_periods,
                         selected_year=selected_year,
                         selected_term=selected_term,
                         is_current=is_current)

def _compute_balances(selected_year, selected_term):
    current_period = get_current_academic_period()
    all_periods    = get_period_history()
    is_current = (selected_year == current_period.get('year') and
                  selected_term == current_period.get('term'))

    all_students = get_all_documents('students')
    all_students.sort(key=lambda x: (x.get('class_name', ''), x.get('last_name', ''), x.get('first_name', '')))

    all_payments = get_all_documents('fee_payments')
    payments_map = {}
    for p in all_payments:
        key = (p.get('student_id'), p.get('academic_year'), p.get('term'))
        payments_map[key] = payments_map.get(key, 0) + p.get('amount_paid', 0)

    closed_periods = [(p.get('year'), p.get('term')) for p in all_periods if p.get('status') == 'closed']
    fee_structures = {}
    if is_current and closed_periods:
        for p_year, p_term in closed_periods:
            fee_structures[(p_year, p_term)] = get_fee_structure(p_year, p_term)

    has_period = (selected_year and selected_year != 'Not Set' and
                  selected_term and selected_term != 'Not Set')
    selected_fee_structure = get_fee_structure(selected_year, selected_term) if has_period else {}

    balances = []
    for student in all_students:
        sid        = student['id']
        class_name = student.get('class_name', '')
        expected   = selected_fee_structure.get(class_name, 0)
        paid       = payments_map.get((sid, selected_year, selected_term), 0)
        credit     = 0
        if is_current:
            for p_year, p_term in closed_periods:
                prev_fee  = fee_structures.get((p_year, p_term), {}).get(class_name, 0)
                prev_paid = payments_map.get((sid, p_year, p_term), 0)
                if prev_paid > prev_fee:
                    credit += prev_paid - prev_fee
        balances.append({
            'student_number': student.get('student_number', ''),
            'name':           f"{student.get('first_name','')} {student.get('last_name','')}".strip(),
            'class_name':     class_name,
            'expected':       expected,
            'paid':           paid,
            'credit':         credit,
            'balance':        expected - paid - credit,
        })

    balances.sort(key=lambda x: x['balance'], reverse=True)
    return balances, is_current


def _filter_balances(balances, class_filter, status_filter):
    if class_filter:
        balances = [b for b in balances if b['class_name'] == class_filter]
    if status_filter:
        if status_filter == 'balance':
            balances = [b for b in balances if b['balance'] > 0]
        elif status_filter == 'paid':
            balances = [b for b in balances if b['balance'] <= 0]
        elif status_filter == 'credit':
            balances = [b for b in balances if b['balance'] < 0]
    return balances


@admin_bp.route('/student_balances/pdf', methods=['POST'])
@role_required('school_admin', 'accounts')
def student_balances_pdf():
    selected_year  = request.form.get('year', '')
    selected_term  = request.form.get('term', '')
    class_filter   = request.form.get('class_filter', '')
    status_filter  = request.form.get('status_filter', '')

    balances, is_current = _compute_balances(selected_year, selected_term)
    balances = _filter_balances(balances, class_filter, status_filter)

    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter,
                               leftMargin=36, rightMargin=36,
                               topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story  = []

    brand_green = colors.HexColor('#1F7A5C')

    title_style = ParagraphStyle('BTitle', parent=styles['Heading1'],
                                 textColor=brand_green, spaceAfter=4)
    story.append(Paragraph("Student Balances Report", title_style))

    desc_parts = [f"{selected_year} — {selected_term}"]
    if class_filter:
        desc_parts.append(f"Class: {class_filter.title()}")
    if status_filter:
        desc_parts.append(f"Status: {status_filter.title()}")
    story.append(Paragraph(" | ".join(desc_parts), styles['Normal']))
    story.append(Spacer(1, 14))

    headers = ['#', 'Student', 'Std No.', 'Class', 'Expected (MWK)', 'Paid (MWK)', 'Balance (MWK)']
    rows    = [headers]
    for i, b in enumerate(balances, 1):
        bal = b['balance']
        if bal < 0:
            bal_str = f"Credit {abs(bal):,.0f}"
        elif bal == 0:
            bal_str = "Paid"
        else:
            bal_str = f"{bal:,.0f}"
        rows.append([
            str(i),
            b['name'],
            b['student_number'],
            b['class_name'].title() if b['class_name'] else '',
            f"{b['expected']:,.0f}",
            f"{b['paid']:,.0f}",
            bal_str,
        ])

    col_widths = [22, 130, 70, 70, 90, 80, 90]
    tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  brand_green),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 8),
        ('ALIGN',         (4, 0), (-1, -1), 'RIGHT'),
        ('ALIGN',         (0, 0), (0, -1),  'CENTER'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFB')]),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)

    doc.build(story)
    buffer.seek(0)

    fname_parts = [selected_year, selected_term.replace(' ', '')]
    if class_filter:
        fname_parts.append(class_filter.replace(' ', '_'))
    filename = f"student_balances_{'_'.join(p for p in fname_parts if p)}.pdf"

    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


@admin_bp.route('/student_balances/csv', methods=['POST'])
@role_required('school_admin', 'accounts')
def student_balances_csv():
    selected_year  = request.form.get('year', '')
    selected_term  = request.form.get('term', '')
    class_filter   = request.form.get('class_filter', '')
    status_filter  = request.form.get('status_filter', '')

    balances, is_current = _compute_balances(selected_year, selected_term)
    balances = _filter_balances(balances, class_filter, status_filter)

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student Number', 'Class',
                     'Expected (MWK)', 'Paid (MWK)', 'Credit (MWK)', 'Balance (MWK)',
                     'Year', 'Term'])
    for b in balances:
        bal = b['balance']
        bal_str = f"Credit {abs(bal):.2f}" if bal < 0 else ('Paid' if bal == 0 else f"{bal:.2f}")
        writer.writerow([
            b['name'],
            b['student_number'],
            b['class_name'].title() if b['class_name'] else '',
            f"{b['expected']:.2f}",
            f"{b['paid']:.2f}",
            f"{b['credit']:.2f}",
            bal_str,
            selected_year,
            selected_term,
        ])

    fname_parts = [selected_year, selected_term.replace(' ', '')]
    if class_filter:
        fname_parts.append(class_filter.replace(' ', '_'))
    filename = f"student_balances_{'_'.join(p for p in fname_parts if p)}.csv"

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


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
    current_period = get_current_academic_period()
    all_payments = get_all_documents('fee_payments')
    academic_years = sorted(list(set([p.get('academic_year') for p in all_payments if p.get('academic_year')])), reverse=True)
    terms = sorted(list(set([p.get('term') for p in all_payments if p.get('term')])))

    all_students = get_all_documents('students')
    classes = sorted(list(set([s.get('class_name') for s in all_students if s.get('class_name')])))

    return render_template('view_fee_payments.html',
                         academic_years=academic_years,
                         terms=terms,
                         classes=classes,
                         current_period=current_period)

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

    # Fee structure + per-student totals (only meaningful when year+term selected)
    fee_structure = {}
    student_total_paid = {}
    if selected_year and selected_term:
        fee_structure = get_fee_structure(selected_year, selected_term)
        for p in payments:
            sid = p.get('student_id')
            student_total_paid[sid] = student_total_paid.get(sid, 0) + p.get('amount_paid', 0)

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
        payment_dict['class_name'] = student.get('class_name', '')
        payment_dict['full_name'] = f"{student.get('first_name', '')} {student.get('middle_name') or ''} {student.get('last_name', '')}".replace('  ', ' ')

        if payment_dict.get('payment_date'):
            payment_dict['payment_date'] = payment_dict['payment_date'].strftime('%Y-%m-%d') if hasattr(payment_dict['payment_date'], 'strftime') else payment_dict['payment_date']

        if selected_year and selected_term:
            expected = fee_structure.get(student.get('class_name', ''), 0)
            total_paid = student_total_paid.get(payment.get('student_id'), 0)
            payment_dict['balance'] = expected - total_paid
        else:
            payment_dict['balance'] = None

        filtered_payments.append(payment_dict)

    filtered_payments.sort(key=lambda p: p.get('payment_date') or '', reverse=True)

    return jsonify({'payments': filtered_payments})

@admin_bp.route('/edit_fee/<payment_id>', methods=['GET', 'POST'])
@role_required('accounts')
def edit_fee(payment_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        amount_paid   = request.form.get('amount_paid')
        payment_date  = request.form.get('payment_date')
        term          = request.form.get('term')
        academic_year = request.form.get('academic_year')

        if not all([amount_paid, payment_date, term, academic_year]):
            if is_ajax:
                return jsonify({'success': False, 'error': 'Please fill out all fields.'})
            flash("Please fill out all fields.", "error")
            return redirect(url_for('admin.edit_fee', payment_id=payment_id))

        try:
            amount_paid = float(amount_paid)
        except ValueError:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Invalid amount entered.'})
            flash("Invalid amount entered.", "error")
            return redirect(url_for('admin.edit_fee', payment_id=payment_id))

        payment_data = {
            'amount_paid':   amount_paid,
            'payment_date':  datetime.strptime(payment_date, '%Y-%m-%d'),
            'term':          term,
            'academic_year': academic_year
        }

        update_document('fee_payments', payment_id, payment_data)
        log_activity(f"Edited fee payment record (ID: {payment_id}).")

        if is_ajax:
            return jsonify({'success': True})
        flash("Fee payment updated successfully.", "success")
        return redirect(url_for('admin.view_fee_payments'))

    # GET — return JSON for modal pre-fill
    payment = get_document_by_id('fee_payments', payment_id)
    if not payment:
        if is_ajax:
            return jsonify({'success': False, 'error': 'Payment record not found.'})
        flash("Fee payment record not found.", "error")
        return redirect(url_for('admin.view_fee_payments'))

    student = get_document_by_id('students', payment.get('student_id'))
    if student:
        payment['student_name'] = f"{student.get('first_name','')} {student.get('last_name','')}".strip()
        payment['student_number'] = student.get('student_number', '')

    if payment.get('payment_date'):
        payment['payment_date'] = payment['payment_date'].strftime('%Y-%m-%d') if hasattr(payment['payment_date'], 'strftime') else payment['payment_date']

    if is_ajax:
        return jsonify({
            'success':        True,
            'amount_paid':    payment.get('amount_paid'),
            'payment_date':   payment.get('payment_date'),
            'term':           payment.get('term'),
            'academic_year':  payment.get('academic_year'),
            'student_name':   payment.get('student_name', ''),
            'student_number': payment.get('student_number', ''),
        })

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

        if term != 'Term 3':
            flash("Promotions can only be processed at the end of Term 3.", "error")
            return redirect(url_for('admin.promote_students'))

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
                update_document('students', student_id, {'status': 'repeating'})
                skipped += 1
                continue

            scores = [r.get('final_score', 0) for r in student_results]
            average = sum(scores) / len(scores)
            if average < PASS_MARK:
                update_document('students', student_id, {'status': 'repeating'})
                skipped += 1
                continue

            if class_name in CLASS_ORDER:
                idx = CLASS_ORDER.index(class_name)
                if idx < len(CLASS_ORDER) - 1:
                    update_document('students', student_id, {'class_name': CLASS_ORDER[idx + 1], 'status': 'active'})
                    promoted += 1
                elif idx == len(CLASS_ORDER) - 1:
                    # Standard 8 - mark as graduated
                    update_document('students', student_id, {'status': 'graduated'})
                    promoted += 1

        log_activity(f"Promoted {promoted} students after {year} - {term}")
        msg = f"{promoted} student(s) promoted successfully."
        if skipped:
            msg += f" {skipped} skipped (incomplete results or below pass mark) - flagged as repeating."
        flash(msg, "success")
        return redirect(url_for('admin.promote_students'))

    # GET - calculate results
    current_period = get_current_academic_period()
    year = current_period.get('year')
    term = current_period.get('term')
    is_term3 = (term == 'Term 3')

    if not is_term3:
        return render_template('promote_students.html',
                             student_data=[],
                             current_period=current_period,
                             pass_mark=PASS_MARK,
                             is_term3=False)

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
                         pass_mark=PASS_MARK,
                         is_term3=True)

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
@role_required('school_admin', 'teacher')
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
        student_results = [r for r in all_results if r.get('student_id') == sid]

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

    total_students = len(results_data)
    # Sort by average descending and assign positions
    ranked = sorted([r for r in results_data if r['average'] is not None],
                    key=lambda x: x['average'], reverse=True)
    unranked = [r for r in results_data if r['average'] is None]
    for i, r in enumerate(ranked):
        r['position'] = i + 1
        r['total_students'] = total_students
    for r in unranked:
        r['position'] = None
        r['total_students'] = total_students

    return jsonify(ranked + unranked)

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

    # Sort by average descending and assign positions
    results_with_avg = sorted([r for r in results_data if any(s.get('score') is not None for s in r['subjects'])],
                              key=lambda x: (sum(s['score'] for s in x['subjects'] if s.get('score') is not None) /
                                             max(len([s for s in x['subjects'] if s.get('score') is not None]), 1)),
                              reverse=True)
    results_no_avg = [r for r in results_data if r not in results_with_avg]
    for i, r in enumerate(results_with_avg):
        r['position'] = i + 1
    for r in results_no_avg:
        r['position'] = None
    results_data = results_with_avg + results_no_avg

    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    brand_green = colors.Color(31/255, 122/255, 92/255)
    brand_dark  = colors.Color(30/255, 41/255, 59/255)

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1,
                                 textColor=brand_dark, fontSize=14)
    sub_style   = ParagraphStyle('Sub', parent=styles['Normal'], alignment=1,
                                 textColor=colors.grey, fontSize=9)

    story.append(Paragraph("HARMONY SCHOOL", title_style))
    story.append(Paragraph(f"Class Results &mdash; {class_name.title()}", title_style))
    story.append(Paragraph(f"{term} &bull; {academic_year}", sub_style))
    if subject_filter:
        story.append(Paragraph(f"Subject: {subject_filter}", sub_style))
    story.append(Spacer(1, 14))

    if results_data:
        all_subjects = set()
        for student in results_data:
            for subj in student['subjects']:
                all_subjects.add(subj['subject'])
        subjects_list = sorted(list(all_subjects))

        header = ['Pos', 'Student Name', 'Std. No.'] + subjects_list + ['Avg', 'Status']
        table_data = [header]

        for student in results_data:
            subject_scores = {subj['subject']: subj['score'] for subj in student['subjects']}
            scores_vals = [subject_scores.get(s) for s in subjects_list]
            valid = [v for v in scores_vals if v is not None]
            avg = round(sum(valid) / len(valid), 1) if valid else None
            passed = avg >= 40 if avg is not None else None
            pos = str(student['position']) if student.get('position') else '—'

            row = [pos, student['name'], student['student_number']]
            row += [str(s) if s is not None else '—' for s in scores_vals]
            row += [str(avg) if avg is not None else '—',
                    'PASS' if passed else ('FAIL' if passed is False else '—')]
            table_data.append(row)

        n_subj = len(subjects_list)
        col_widths = [28, 110, 60] + [40] * n_subj + [35, 38]
        result_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), brand_green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.Color(0.97, 0.97, 0.97)]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(result_table)

        passed_count = sum(1 for r in results_data if r.get('position'))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Total students: {len(results_data)} &nbsp;&nbsp; With results: {passed_count}",
            ParagraphStyle('footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
        ))
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

@admin_bp.route('/student_report_card/<student_id>')
@role_required('school_admin', 'teacher')
def student_report_card_pdf(student_id):
    from academic_helpers import get_subjects_for_class
    term         = request.args.get('term', '')
    academic_year = request.args.get('year', '')

    if not term or not academic_year:
        flash("Term and academic year are required.", "error")
        return redirect(url_for('admin.view_all_results'))

    student = get_document_by_id('students', student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('admin.view_all_results'))

    class_name        = student.get('class_name', '')
    required_subjects = get_subjects_for_class(class_name)

    # Fetch all results for this class/term/year (needed for position)
    class_students = get_documents_where('students', 'class_name', '==', class_name)
    all_results    = get_documents_by_filters('exam_results', [
        ('term', '==', term), ('academic_year', '==', academic_year)
    ])

    # Build per-student averages for ranking
    class_avgs = []
    for cs in class_students:
        s_scores = [r.get('final_score', 0) for r in all_results if r.get('student_id') == cs['id']]
        if s_scores:
            class_avgs.append(round(sum(s_scores) / len(s_scores), 1))
    class_avgs.sort(reverse=True)

    # This student's results
    my_results = [r for r in all_results if r.get('student_id') == student_id]
    my_scores_map = {r.get('subject'): r.get('final_score') for r in my_results}
    my_scores = [v for v in my_scores_map.values() if v is not None]
    my_average = round(sum(my_scores) / len(my_scores), 1) if my_scores else None
    my_position = None
    if my_average is not None:
        # Find rank (1-based); handle ties by finding first occurrence
        try:
            my_position = class_avgs.index(my_average) + 1
        except ValueError:
            my_position = None

    total_students = len(class_students)

    def get_grade(score):
        if score >= 80: return 'A', 'Distinction'
        if score >= 65: return 'B', 'Merit'
        if score >= 50: return 'C', 'Credit'
        if score >= 40: return 'D', 'Pass'
        return 'F', 'Fail'

    def ordinal(n):
        s = ['th','st','nd','rd']
        v = n % 100
        return str(n) + (s[v % 10] if v % 10 < 4 and not 11 <= v <= 13 else s[0])

    # Build subject rows using required_subjects order
    all_subject_keys = required_subjects if required_subjects else sorted(my_scores_map.keys())
    subject_rows = []
    for subj in all_subject_keys:
        score = my_scores_map.get(subj)
        if score is not None:
            grade, remarks = get_grade(score)
        else:
            grade, remarks = '—', 'Not entered'
        subject_rows.append((subj, score if score is not None else '—', grade, remarks))

    # --- PDF generation ---
    buffer       = BytesIO()
    brand_green  = colors.Color(31/255, 122/255, 92/255)
    brand_dark   = colors.Color(30/255, 41/255, 59/255)
    light_green  = colors.Color(232/255, 245/255, 240/255)

    from reportlab.lib.units import inch
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            leftMargin=0.7*inch, rightMargin=0.7*inch,
                            topMargin=0.6*inch, bottomMargin=0.6*inch)
    styles = getSampleStyleSheet()
    story  = []

    def para(text, **kw):
        return Paragraph(text, ParagraphStyle('x', parent=styles['Normal'], **kw))

    # Header banner
    header_data = [[para('HARMONY SCHOOL',
                          fontSize=16, fontName='Helvetica-Bold',
                          textColor=colors.white, alignment=1),
                    para('STUDENT REPORT CARD',
                          fontSize=11, textColor=colors.white, alignment=1)]]
    header_tbl = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), brand_green),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING',   (0,0), (-1,-1), 12),
        ('RIGHTPADDING',  (0,0), (-1,-1), 12),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 10))

    # Student info table
    full_name = f"{student.get('first_name','')} {student.get('middle_name') or ''} {student.get('last_name','')}".replace('  ',' ').strip()
    info_data = [
        [para('Student Name', fontSize=8, textColor=colors.grey),
         para(full_name, fontSize=10, fontName='Helvetica-Bold', textColor=brand_dark),
         para('Academic Year', fontSize=8, textColor=colors.grey),
         para(academic_year, fontSize=10, fontName='Helvetica-Bold', textColor=brand_dark)],
        [para('Student No.', fontSize=8, textColor=colors.grey),
         para(str(student.get('student_number','')), fontSize=10, textColor=brand_dark),
         para('Term', fontSize=8, textColor=colors.grey),
         para(term, fontSize=10, fontName='Helvetica-Bold', textColor=brand_dark)],
        [para('Class', fontSize=8, textColor=colors.grey),
         para(class_name.title(), fontSize=10, textColor=brand_dark),
         para('Date Printed', fontSize=8, textColor=colors.grey),
         para(datetime.now().strftime('%d %B %Y'), fontSize=10, textColor=brand_dark)],
    ]
    info_tbl = Table(info_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    info_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), light_green),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [4]),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 12))

    # Results table
    story.append(para('Academic Results', fontSize=10, fontName='Helvetica-Bold',
                       textColor=brand_dark, spaceAfter=4))
    res_header = ['No.', 'Subject', 'Score (/100)', 'Grade', 'Remarks']
    res_data   = [res_header]
    for idx, (subj, score, grade, remarks) in enumerate(subject_rows, 1):
        res_data.append([str(idx), subj, str(score), grade, remarks])

    res_tbl = Table(res_data, colWidths=[0.4*inch, 2.2*inch, 1.1*inch, 0.7*inch, 1.6*inch],
                    repeatRows=1)
    res_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), brand_green),
        ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('ALIGN',         (1,1), (1,-1), 'LEFT'),
        ('ALIGN',         (4,1), (4,-1), 'LEFT'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_green]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.Color(0.8,0.8,0.8)),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(res_tbl)
    story.append(Spacer(1, 10))

    # Summary box
    passed   = my_average >= 40 if my_average is not None else None
    pos_text = f"{ordinal(my_position)} out of {total_students}" if my_position else f"— out of {total_students}"
    avg_text = f"{my_average}%" if my_average is not None else "—"
    status_text = "PASSED" if passed else ("FAILED" if passed is False else "INCOMPLETE")
    status_color = colors.Color(31/255,122/255,92/255) if passed else (colors.Color(0.85,0.2,0.2) if passed is False else colors.grey)

    summary_data = [
        [para('Average Score', fontSize=8, textColor=colors.grey),
         para(avg_text, fontSize=13, fontName='Helvetica-Bold', textColor=brand_dark, alignment=1),
         para('Position', fontSize=8, textColor=colors.grey),
         para(pos_text, fontSize=11, fontName='Helvetica-Bold', textColor=brand_dark, alignment=1),
         para('Result', fontSize=8, textColor=colors.grey),
         para(status_text, fontSize=13, fontName='Helvetica-Bold', textColor=status_color, alignment=1)],
    ]
    sum_tbl = Table(summary_data, colWidths=[0.9*inch, 1.5*inch, 0.8*inch, 2.0*inch, 0.7*inch, 1.1*inch])
    sum_tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), colors.Color(0.97,0.97,0.97)),
        ('BOX',           (0,0), (-1,-1), 1, brand_green),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 18))

    # Signature section
    sig_data = [
        [para("Class Teacher: _______________________", fontSize=9),
         para("Date: _______________", fontSize=9)],
        [para("Head Teacher:  _______________________", fontSize=9),
         para("Date: _______________", fontSize=9)],
        [para("Parent / Guardian: ___________________", fontSize=9),
         para("Date: _______________", fontSize=9)],
    ]
    sig_tbl = Table(sig_data, colWidths=[4.5*inch, 2.5*inch])
    sig_tbl.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sig_tbl)

    doc.build(story)
    buffer.seek(0)

    safe_name = f"{student.get('first_name','')}_{student.get('last_name','')}".replace(' ','_')
    student_no = student.get('student_number', '').replace(' ', '_')
    response  = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = \
        f'attachment; filename={safe_name}_{student_no}_{term.replace(" ","_")}_{academic_year}_Report_Card.pdf'
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
@role_required('school_admin', 'accounts')
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

@admin_bp.route('/manage_classes', methods=['GET', 'POST'])
@role_required('school_admin')
def manage_classes():
    db = get_firestore_db()
    school_id = get_school_id()
    classes_ref = db.collection('schools').document(school_id).collection('classes')

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_class':
            class_name = request.form.get('class_name', '').strip().lower()
            if not class_name:
                flash("Class name cannot be empty.", "error")
            else:
                existing = [doc.id for doc in classes_ref.stream()]
                if class_name in existing:
                    flash("Class already exists.", "error")
                else:
                    classes_ref.document(class_name).set({'name': class_name, 'order': len(existing)})
                    log_activity(f"Added class: {class_name}")
                    flash(f"Class '{class_name.title()}' added.", "success")

        elif action == 'remove_class':
            class_name = request.form.get('class_name')
            students = get_documents_where('students', 'class_name', '==', class_name)
            if students:
                flash(f"Cannot remove '{class_name.title()}' - it has {len(students)} student(s) enrolled.", "error")
            else:
                classes_ref.document(class_name).delete()
                log_activity(f"Removed class: {class_name}")
                flash(f"Class '{class_name.title()}' removed.", "success")

        return redirect(url_for('admin.manage_classes'))

    # Get classes ordered
    CLASS_ORDER = ['nursery', 'reception', 'standard 1', 'standard 2', 'standard 3',
                   'standard 4', 'standard 5', 'standard 6', 'standard 7', 'standard 8']
    all_students = get_all_documents('students')
    class_counts = {}
    for s in all_students:
        cn = s.get('class_name', '')
        class_counts[cn] = class_counts.get(cn, 0) + 1

    classes = []
    for cn in CLASS_ORDER:
        classes.append({'name': cn, 'count': class_counts.get(cn, 0)})

    return render_template('manage_classes.html', classes=classes)

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

@admin_bp.route('/get_class_positions', methods=['POST'])
@role_required('school_admin', 'teacher')
def get_class_positions():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')

    if not all([class_name, term, academic_year]):
        return jsonify([])

    students = get_documents_where('students', 'class_name', '==', class_name)
    all_results = get_documents_by_filters('exam_results', [
        ('term', '==', term), ('academic_year', '==', academic_year)
    ])

    positions = []
    for student in students:
        sid = student['id']
        student_results = [r for r in all_results if r.get('student_id') == sid]
        scores = [r.get('final_score', 0) for r in student_results]
        average = round(sum(scores) / len(scores), 1) if scores else None
        positions.append({
            'id': sid,
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'average': average,
            'subjects_count': len(student_results)
        })

    # Sort by average descending, assign positions
    with_results = sorted([p for p in positions if p['average'] is not None], key=lambda x: x['average'], reverse=True)
    no_results = [p for p in positions if p['average'] is None]

    for i, p in enumerate(with_results):
        p['position'] = i + 1
    for p in no_results:
        p['position'] = None

    return jsonify(with_results + no_results)

@admin_bp.route('/mark_student_status', methods=['POST'])
@role_required('school_admin')
def mark_student_status():
    student_id = request.form.get('student_id')
    status = request.form.get('status')  # 'graduated', 'repeating', 'active'

    if not student_id or not status:
        return jsonify({'success': False})

    update_document('students', student_id, {'status': status})
    student = get_document_by_id('students', student_id)
    name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip() if student else student_id
    log_activity(f"Marked student '{name}' as {status}")
    return jsonify({'success': True})

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
