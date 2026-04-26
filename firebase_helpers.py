"""
Firebase Helper Functions
Common database operations for Firebase Firestore
"""

from firebase_db import get_firestore_db, get_school_id
from datetime import datetime

def get_all_documents(collection_name):
    """Get all documents from a collection"""
    db = get_firestore_db()
    school_id = get_school_id()
    docs = db.collection('schools').document(school_id).collection(collection_name).stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]

def get_document_by_id(collection_name, doc_id):
    """Get a single document by ID"""
    db = get_firestore_db()
    school_id = get_school_id()
    doc = db.collection('schools').document(school_id).collection(collection_name).document(doc_id).get()
    if doc.exists:
        return {'id': doc.id, **doc.to_dict()}
    return None

def get_documents_where(collection_name, field, operator, value):
    """Query documents with a where clause"""
    return get_documents_by_filters(collection_name, [(field, operator, value)])

def get_documents_by_filters(collection_name, filters):
    """Query documents using multiple where filters"""
    db = get_firestore_db()
    school_id = get_school_id()
    collection_ref = db.collection('schools').document(school_id).collection(collection_name)
    for field, operator, value in filters:
        collection_ref = collection_ref.where(field, operator, value)
    docs = collection_ref.stream()
    return [{'id': doc.id, **doc.to_dict()} for doc in docs]


def add_document(collection_name, data):
    """Add a new document"""
    db = get_firestore_db()
    school_id = get_school_id()
    doc_ref = db.collection('schools').document(school_id).collection(collection_name).add(data)
    return doc_ref[1].id

def update_document(collection_name, doc_id, data):
    """Update an existing document"""
    db = get_firestore_db()
    school_id = get_school_id()
    db.collection('schools').document(school_id).collection(collection_name).document(doc_id).update(data)

def delete_document(collection_name, doc_id):
    """Delete a document"""
    db = get_firestore_db()
    school_id = get_school_id()
    db.collection('schools').document(school_id).collection(collection_name).document(doc_id).delete()

def count_documents(collection_name):
    """Count documents in a collection"""
    return len(get_all_documents(collection_name))

def count_documents_where(collection_name, field, operator, value):
    """Count documents matching a condition"""
    return len(get_documents_where(collection_name, field, operator, value))
