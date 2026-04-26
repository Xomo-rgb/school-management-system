from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify, Response
from firebase_helpers import *
from utils import role_required
from academic_helpers import get_current_academic_period, get_period_history
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import StringIO, BytesIO
import csv

teacher_bp = Blueprint('teacher', __name__)

def get_teacher_data():
    """Helper to get current teacher's profile and assignments"""
    teacher = get_document_by_id('users', session.get('user_id'))
    assignments = teacher.get('assignments', []) if teacher else []
    return teacher, assignments

@teacher_bp.route('/dashboard', endpoint='teacher_dashboard')
@role_required('teacher')
def teacher_dashboard():
    teacher, assignments = get_teacher_data()
    assigned_class_names = [a['class_name'] for a in assignments]
    student_count = 0
    if assigned_class_names:
        students = get_documents_by_filters('students', [('class_name', 'in', assigned_class_names)])
        student_count = len(students)
    current_period = get_current_academic_period()

    return render_template('teacher_dashboard.html',
                         assignments=assignments,
                         class_count=len(assignments),
                         student_count=student_count,
                         current_period=current_period)

@teacher_bp.route('/enter_results', methods=['GET', 'POST'])
@role_required('teacher', 'school_admin')
def enter_results():
    from academic_helpers import get_subjects_for_class

    teacher, assignments = get_teacher_data()
    current_period = get_current_academic_period()
    all_periods = get_period_history()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        class_name = request.form.get('class_name')
        term = request.form.get('term')
        academic_year = request.form.get('academic_year')
        subjects = request.form.getlist('subject[]')
        scores = request.form.getlist('score[]')

        if not all([student_id, class_name, term, academic_year]) or not subjects:
            flash("Please fill out all fields.", "error")
            return redirect(url_for('teacher.enter_results'))

        saved = 0
        for subject, score in zip(subjects, scores):
            if not subject or score == '':
                continue
            try:
                score_val = float(score)
                if score_val < 0 or score_val > 100:
                    continue
            except ValueError:
                continue

            # Load existing results for this student/term/year once
            existing_results = get_documents_by_filters('exam_results', [
                ('student_id', '==', student_id),
                ('term', '==', term),
                ('academic_year', '==', academic_year)
            ])
            existing_by_subject = {r.get('subject'): r for r in existing_results}

            result_data = {
                'student_id': student_id,
                'class_name': class_name,
                'subject': subject,
                'term': term,
                'academic_year': academic_year,
                'final_score': score_val,
                'entered_by': session.get('user_id')
            }

            if existing_by_subject.get(subject):
                update_document('exam_results', existing_by_subject[subject]['id'], result_data)
            else:
                add_document('exam_results', result_data)
            saved += 1

        flash(f"Results saved successfully for {saved} subject(s).", "success")
        return redirect(url_for('teacher.enter_results'))

    return render_template('enter_results.html',
                         assignments=assignments,
                         current_period=current_period,
                         all_periods=all_periods)

@teacher_bp.route('/get_students_for_class', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_students_for_class():
    class_name = request.form.get('class_name')
    if not class_name:
        return jsonify([])

    # For teachers, verify they are assigned to this class
    if session.get('role') == 'teacher':
        teacher, assignments = get_teacher_data()
        assigned_classes = [a['class_name'] for a in assignments]
        if class_name not in assigned_classes:
            return jsonify([])

    students = get_documents_where('students', 'class_name', '==', class_name)
    students.sort(key=lambda x: (x.get('last_name', ''), x.get('first_name', '')))

    return jsonify([{
        'id': s['id'],
        'name': f"{s.get('first_name', '')} {s.get('last_name', '')}".strip(),
        'student_number': s.get('student_number', '')
    } for s in students])

@teacher_bp.route('/get_existing_results', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_existing_results():
    student_id = request.form.get('student_id')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')

    if not all([student_id, term, academic_year]):
        return jsonify([])

    results = get_documents_by_filters('exam_results', [
        ('student_id', '==', student_id),
        ('term', '==', term),
        ('academic_year', '==', academic_year)
    ])

    return jsonify([{'subject': r.get('subject'), 'score': r.get('final_score')} for r in results])

@teacher_bp.route('/view_results')
@role_required('teacher', 'school_admin')
def view_results():
    teacher, assignments = get_teacher_data()
    current_period = get_current_academic_period()
    all_periods = get_period_history()

    return render_template('view_results.html',
                         assignments=assignments,
                         current_period=current_period,
                         all_periods=all_periods)

@teacher_bp.route('/get_class_results', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_class_results():
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

@teacher_bp.route('/view_results/pdf', methods=['POST'])
@role_required('teacher', 'school_admin')
def view_results_pdf():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject_filter = request.form.get('subject_filter', '')

    if not all([class_name, term, academic_year]):
        flash("Please select class, term, and academic year.", "error")
        return redirect(url_for('teacher.view_results'))

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

        results_data.append({
            'name': f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            'student_number': student.get('student_number', ''),
            'subjects': [{'subject': r.get('subject'), 'score': r.get('final_score')} for r in student_results],
        })

    results_data.sort(key=lambda x: x['name'])

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1)
    story.append(Paragraph(f"Teacher Results Report - {class_name.title()}", title_style))
    story.append(Paragraph(f"Term: {term} | Academic Year: {academic_year}", styles['Heading3']))
    if subject_filter:
        story.append(Paragraph(f"Subject: {subject_filter}", styles['Heading3']))
    story.append(Spacer(1, 12))

    if results_data:
        all_subjects = set()
        for student in results_data:
            for subj in student['subjects']:
                all_subjects.add(subj['subject'])
        subjects_list = sorted(list(all_subjects))
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
    filename = f"teacher_results_{class_name}_{term}_{academic_year}.pdf"
    if subject_filter:
        filename = f"teacher_results_{class_name}_{subject_filter}_{term}_{academic_year}.pdf"
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@teacher_bp.route('/view_results/csv', methods=['POST'])
@role_required('teacher', 'school_admin')
def view_results_csv():
    class_name = request.form.get('class_name')
    term = request.form.get('term')
    academic_year = request.form.get('academic_year')
    subject_filter = request.form.get('subject_filter', '')

    if not all([class_name, term, academic_year]):
        flash("Please select class, term, and academic year.", "error")
        return redirect(url_for('teacher.view_results'))

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

    filename = f"teacher_results_{class_name}_{term}_{academic_year}.csv"
    if subject_filter:
        filename = f"teacher_results_{class_name}_{subject_filter}_{term}_{academic_year}.csv"
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@teacher_bp.route('/delete_result/<result_id>', methods=['POST'])
@role_required('teacher', 'school_admin')
def delete_result(result_id):
    delete_document('exam_results', result_id)
    flash("Result deleted.", "success")
    return redirect(url_for('teacher.view_results'))

@teacher_bp.route('/get_students_for_results', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_students_for_results():
    return jsonify([])

@teacher_bp.route('/get_student_report_card', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_student_report_card():
    return jsonify({'success': False, 'message': 'Not yet implemented'})

@teacher_bp.route('/get_subject_report', methods=['POST'])
@role_required('teacher', 'school_admin')
def get_subject_report():
    return jsonify({'success': False, 'message': 'Not yet implemented'})
