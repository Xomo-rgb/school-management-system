from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from firebase_db import get_firestore_db, get_school_id
from firebase_helpers import *
from utils import role_required, log_activity
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO

student_bp = Blueprint('student', __name__)

@student_bp.route('/profile/<student_id>')
@role_required('teacher', 'school_admin', 'accounts')
def profile(student_id):
    from academic_helpers import get_current_academic_period, get_fee_for_class
    
    student = get_document_by_id('students', student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('student.view_students'))
    
    results = get_documents_where('exam_results', 'student_id', '==', student_id)
    payments = get_documents_where('fee_payments', 'student_id', '==', student_id)
    
    # Ensure payment dates are datetime objects
    for p in payments:
        if p.get('payment_date'):
            if isinstance(p['payment_date'], str):
                # If it's a string, try to parse it
                try:
                    p['payment_date'] = datetime.strptime(p['payment_date'], '%Y-%m-%d')
                except ValueError:
                    p['payment_date'] = None

    
    # Calculate fee balance for current period
    current_period = get_current_academic_period()
    year = current_period.get('year')
    term = current_period.get('term')
    expected_fee = get_fee_for_class(student.get('class_name', ''), year, term)
    current_term_paid = sum(
        p.get('amount_paid', 0) for p in payments
        if p.get('academic_year') == year and p.get('term') == term
    )
    balance = expected_fee - current_term_paid
    
    return render_template('student_profile.html',
                         student=student,
                         results=results,
                         payments=payments,
                         current_period=current_period,
                         expected_fee=expected_fee,
                         current_term_paid=current_term_paid,
                         balance=balance)

@student_bp.route('/profile/<student_id>/pdf')
@role_required('school_admin', 'accounts')
def student_profile_pdf(student_id):
    from academic_helpers import get_current_academic_period, get_fee_for_class
    
    student = get_document_by_id('students', student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('student.view_students'))
    
    results = get_documents_where('exam_results', 'student_id', '==', student_id)
    payments = get_documents_where('fee_payments', 'student_id', '==', student_id)
    
    # Ensure payment dates are datetime objects
    for p in payments:
        if p.get('payment_date'):
            if isinstance(p['payment_date'], str):
                try:
                    p['payment_date'] = datetime.strptime(p['payment_date'], '%Y-%m-%d')
                except ValueError:
                    p['payment_date'] = None
    
    # Calculate fee balance for current period
    current_period = get_current_academic_period()
    year = current_period.get('year')
    term = current_period.get('term')
    expected_fee = get_fee_for_class(student.get('class_name', ''), year, term)
    current_term_paid = sum(
        p.get('amount_paid', 0) for p in payments
        if p.get('academic_year') == year and p.get('term') == term
    )
    balance = expected_fee - current_term_paid
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph("Student Profile Report", title_style))
    story.append(Spacer(1, 12))
    
    # Student Information
    story.append(Paragraph("Student Information", styles['Heading2']))
    student_info = [
        ["Student Number:", student.get('student_number', 'N/A')],
        ["Name:", f"{student.get('first_name', '')} {student.get('middle_name', '')} {student.get('last_name', '')}".strip()],
        ["Class:", student.get('class_name', 'N/A')],
        ["Date of Birth:", student.get('date_of_birth', 'N/A')],
        ["Gender:", student.get('gender', 'N/A')],
        ["Guardian Name:", student.get('guardian_name', 'N/A')],
        ["Guardian Phone:", student.get('guardian_phone', 'N/A')],
        ["Address:", student.get('address', 'N/A')],
    ]
    student_table = Table(student_info, colWidths=[120, 300])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 12))
    
    # Academic Results
    story.append(Paragraph("Academic Results", styles['Heading2']))
    if results:
        result_data = [["Year", "Term", "Subject", "Grade"]]
        for result in results:
            result_data.append([
                result.get('academic_year', ''),
                result.get('term', ''),
                result.get('subject', ''),
                result.get('grade', ''),
            ])
        result_table = Table(result_data, colWidths=[80, 80, 150, 80])
        result_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(result_table)
    else:
        story.append(Paragraph("No academic results found.", styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Fee Payment History
    story.append(Paragraph("Fee Payment History", styles['Heading2']))
    if payments:
        payment_data = [["Date", "Amount", "Term", "Year"]]
        for payment in payments:
            date_str = payment['payment_date'].strftime('%d-%b-%Y') if payment.get('payment_date') and hasattr(payment['payment_date'], 'strftime') else 'Unknown'
            payment_data.append([
                date_str,
                f"{payment.get('amount_paid', 0):.2f}",
                payment.get('term', ''),
                payment.get('academic_year', ''),
            ])
        payment_table = Table(payment_data, colWidths=[80, 80, 80, 80])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(payment_table)
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Current Period ({current_period.get('term')} {current_period.get('year')}): Expected Fee: {expected_fee:.2f}, Paid: {current_term_paid:.2f}, Balance: {balance:.2f}", styles['Normal']))
    else:
        story.append(Paragraph("No fee payments found.", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename=student_profile_{student.get("student_number", student_id)}.pdf'
    return response

@student_bp.route('/register', methods=['GET', 'POST'])
@role_required('school_admin')
def register_student():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        dob = request.form.get('dob')
        middle_name = request.form.get('middle_name')
        gender = request.form.get('gender')
        class_name = request.form.get('class_name')
        guardian_contact = request.form.get('guardian_contact')
        government_number = request.form.get('government_number', '').strip()
        special_needs = request.form.get('special_needs')
        address = request.form.get('address')
        enrollment_date = request.form.get('enrollment_date')

        if not all([first_name, last_name, dob, gender, class_name, guardian_contact, address, enrollment_date]):
            flash("Please fill out all required (*) fields.", "error")
            return render_template('register_student.html', form_data=request.form)

        no_gov_classes = ['nursery', 'reception']
        if class_name not in no_gov_classes and not government_number:
            flash("Government number is required for Standard 1 and above.", "error")
            return render_template('register_student.html', form_data=request.form)

        if government_number:
            existing = get_documents_where('students', 'government_number', '==', government_number)
            if existing:
                flash(f"The government number '{government_number}' is already assigned to another student.", "error")
                return render_template('register_student.html', form_data=request.form)
        
        all_students = get_all_documents('students')
        max_id = max([int(s.get('student_number', 'HS-2025-000').split('-')[-1]) for s in all_students] + [0])
        student_number = f"HS-2025-{str(max_id + 1).zfill(3)}"
        
        student_data = {
            'student_number': student_number,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'dob': datetime.strptime(dob, '%Y-%m-%d') if dob else None,
            'gender': gender,
            'class_name': class_name,
            'guardian_contact': guardian_contact,
            'government_number': government_number if government_number else None,
            'special_needs': special_needs,
            'address': address,
            'enrollment_date': datetime.strptime(enrollment_date, '%Y-%m-%d') if enrollment_date else None
        }
        
        add_document('students', student_data)
        log_activity(f"Registered new student: '{first_name} {last_name}' with number {student_number}.")
        flash(f"Student '{first_name} {last_name}' registered successfully.", "success")
        return redirect(url_for('student.view_students'))

    return render_template('register_student.html')

@student_bp.route('/edit/<student_id>', methods=['GET', 'POST'])
@role_required('school_admin')
def edit_student(student_id):
    if request.method == 'POST':
        student_data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'middle_name': request.form['middle_name'],
            'dob': datetime.strptime(request.form['dob'], '%Y-%m-%d') if request.form.get('dob') else None,
            'gender': request.form['gender'],
            'class_name': request.form['class_name'],
            'guardian_contact': request.form['guardian_contact'],
            'government_number': request.form['government_number'],
            'special_needs': request.form['special_needs'],
            'address': request.form['address'],
            'enrollment_date': datetime.strptime(request.form['enrollment_date'], '%Y-%m-%d') if request.form.get('enrollment_date') else None
        }
        
        update_document('students', student_id, student_data)
        log_activity(f"Edited student record for '{student_data['first_name']} {student_data['last_name']}' (ID: {student_id}).")
        flash("Student information updated successfully.", "success")
        return redirect(url_for('student.view_students'))
    
    student = get_document_by_id('students', student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('student.view_students'))
    
    if student.get('dob'):
        student['dob'] = student['dob'].strftime('%Y-%m-%d') if hasattr(student['dob'], 'strftime') else student['dob']
    if student.get('enrollment_date'):
        student['enrollment_date'] = student['enrollment_date'].strftime('%Y-%m-%d') if hasattr(student['enrollment_date'], 'strftime') else student['enrollment_date']
    
    return render_template('edit_student.html', student=student)

@student_bp.route('/delete/<student_id>', methods=['POST'])
@role_required('school_admin')
def delete_student(student_id):
    student = get_document_by_id('students', student_id)
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for('student.view_students'))
    
    student_name = f"{student['first_name']} {student['last_name']}"
    delete_document('students', student_id)
    log_activity(f"Deleted student record for '{student_name}' (ID: {student_id}).")
    flash("Student deleted successfully.", "success")
    return redirect(url_for('student.view_students'))

@student_bp.route('/')
@role_required('teacher', 'school_admin', 'accounts')
def view_students():
    students = get_all_documents('students')
    
    # Teachers only see students in their assigned classes
    if session.get('role') == 'teacher':
        teacher = get_document_by_id('users', session.get('user_id'))
        assigned_classes = [a['class_name'] for a in teacher.get('assignments', [])]
        students = [s for s in students if s.get('class_name') in assigned_classes]
    
    students.sort(key=lambda x: (x.get('class_name', ''), x.get('last_name', ''), x.get('first_name', '')))
    
    teacher_assignments = []
    if session.get('role') == 'teacher':
        teacher = get_document_by_id('users', session.get('user_id'))
        teacher_assignments = teacher.get('assignments', [])
    
    return render_template('view_students.html', students=students, teacher_assignments=teacher_assignments)

@student_bp.route('/filter', methods=['POST'])
@role_required('teacher', 'school_admin', 'accounts')
def filter_students():
    selected_class = request.form.get('class_name')

    # Get teacher's assigned classes if role is teacher
    assigned_classes = None
    if session.get('role') == 'teacher':
        teacher = get_document_by_id('users', session.get('user_id'))
        assigned_classes = [a['class_name'] for a in teacher.get('assignments', [])]

    if selected_class:
        # If teacher, make sure selected class is in their assignments
        if assigned_classes is not None and selected_class not in assigned_classes:
            return jsonify({'students': []})
        students = get_documents_where('students', 'class_name', '==', selected_class)
    else:
        students = get_all_documents('students')
        if assigned_classes is not None:
            students = [s for s in students if s.get('class_name') in assigned_classes]
    
    students.sort(key=lambda x: (x.get('last_name', ''), x.get('first_name', '')))
    
    students_list = []
    for s in students:
        s_dict = dict(s)
        if s_dict.get('dob'):
            s_dict['dob'] = s_dict['dob'].strftime('%Y-%m-%d') if hasattr(s_dict['dob'], 'strftime') else s_dict['dob']
        if s_dict.get('enrollment_date'):
            s_dict['enrollment_date'] = s_dict['enrollment_date'].strftime('%Y-%m-%d') if hasattr(s_dict['enrollment_date'], 'strftime') else s_dict['enrollment_date']
        s_dict['full_name'] = f"{s_dict.get('first_name', '')} {s_dict.get('middle_name') or ''} {s_dict.get('last_name', '')}".replace('  ', ' ')
        students_list.append(s_dict)
    
    return jsonify({"students": students_list})
