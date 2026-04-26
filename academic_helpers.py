from firebase_db import get_firestore_db, get_school_id
from datetime import datetime

def get_subjects_for_class(class_name):
    """Get subjects for a specific class"""
    db = get_firestore_db()
    school_id = get_school_id()
    doc = db.collection('schools').document(school_id).collection('subjects').document(class_name).get()
    if doc.exists:
        return doc.to_dict().get('subjects', [])
    return []

def get_all_subjects():
    """Get all subjects grouped by class"""
    db = get_firestore_db()
    school_id = get_school_id()
    docs = db.collection('schools').document(school_id).collection('subjects').stream()
    return {doc.id: doc.to_dict().get('subjects', []) for doc in docs}

def save_subjects_for_class(class_name, subjects):
    """Save subjects for a specific class"""
    db = get_firestore_db()
    school_id = get_school_id()
    db.collection('schools').document(school_id).collection('subjects').document(class_name).set({'subjects': subjects})

def get_current_academic_period():
    """Get current active academic period"""
    db = get_firestore_db()
    school_id = get_school_id()

    periods_ref = db.collection('schools').document(school_id).collection('academic_periods')
    active = periods_ref.where('status', '==', 'active').limit(1).stream()

    for doc in active:
        data = doc.to_dict()
        data['id'] = doc.id
        return data

    return {'year': 'Not Set', 'term': 'Not Set', 'status': 'none'}

def get_period_history():
    """Get all academic periods ordered by most recent"""
    db = get_firestore_db()
    school_id = get_school_id()

    periods_ref = db.collection('schools').document(school_id).collection('academic_periods')
    all_periods = periods_ref.stream()

    history = []
    for doc in all_periods:
        data = doc.to_dict()
        data['id'] = doc.id
        if data.get('closed_at') and hasattr(data['closed_at'], 'strftime'):
            data['closed_at'] = data['closed_at'].strftime('%d %b %Y')
        history.append(data)

    # Sort: active first, then by year/term descending
    history.sort(key=lambda x: (x.get('status') != 'active', x.get('year', ''), x.get('term', '')), reverse=False)
    return history

def start_new_period(year, term):
    """Start a new academic period"""
    db = get_firestore_db()
    school_id = get_school_id()

    periods_ref = db.collection('schools').document(school_id).collection('academic_periods')
    periods_ref.add({
        'year': year,
        'term': term,
        'status': 'active',
        'started_at': datetime.now(),
        'closed_at': None
    })

def end_current_period():
    """End the current active period"""
    db = get_firestore_db()
    school_id = get_school_id()

    periods_ref = db.collection('schools').document(school_id).collection('academic_periods')
    active = periods_ref.where('status', '==', 'active').limit(1).stream()

    for doc in active:
        periods_ref.document(doc.id).update({
            'status': 'closed',
            'closed_at': datetime.now()
        })
        return True
    return False

def is_period_active(year, term):
    """Check if a given year/term is the active period"""
    current = get_current_academic_period()
    return current.get('year') == year and current.get('term') == term and current.get('status') == 'active'

def get_fee_structure(year, term):
    """Get fee structure for a specific year and term"""
    db = get_firestore_db()
    school_id = get_school_id()

    fee_ref = db.collection('schools').document(school_id).collection('fee_structure').document(f"{year}_{term}")
    fee_doc = fee_ref.get()

    if fee_doc.exists:
        return fee_doc.to_dict()
    return {}

def set_fee_structure(year, term, fee_data):
    """Set fee structure for a specific year and term"""
    db = get_firestore_db()
    school_id = get_school_id()

    fee_ref = db.collection('schools').document(school_id).collection('fee_structure').document(f"{year}_{term}")
    fee_ref.set(fee_data)

def get_fee_for_class(class_name, year, term):
    """Get fee amount for a specific class, year, and term"""
    fee_structure = get_fee_structure(year, term)
    return fee_structure.get(class_name, 0)

def calculate_student_balance(student_id, year, term):
    """Calculate balance for a student in a specific term"""
    from firebase_helpers import get_document_by_id, get_documents_where

    student = get_document_by_id('students', student_id)
    if not student:
        return {'expected': 0, 'paid': 0, 'balance': 0}

    class_name = student.get('class_name', '')
    expected_fee = get_fee_for_class(class_name, year, term)

    all_payments = get_documents_where('fee_payments', 'student_id', '==', student_id)
    paid_amount = sum(
        p.get('amount_paid', 0)
        for p in all_payments
        if p.get('academic_year') == year and p.get('term') == term
    )

    return {
        'expected': expected_fee,
        'paid': paid_amount,
        'balance': expected_fee - paid_amount
    }
