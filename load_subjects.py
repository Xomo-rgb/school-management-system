import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate('firebase-credentials.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()
school_id = 'harmony-school'

DEFAULT_SUBJECTS = {
    'nursery': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts'
    ],
    'reception': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts'
    ],
    'standard 1': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts', 'Life Skills'
    ],
    'standard 2': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts', 'Life Skills'
    ],
    'standard 3': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts', 'Life Skills'
    ],
    'standard 4': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts', 'Life Skills'
    ],
    'standard 5': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts',
        'Life Skills', 'Science & Technology', 'Agriculture', 'Social Studies'
    ],
    'standard 6': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts',
        'Life Skills', 'Science & Technology', 'Agriculture', 'Social Studies'
    ],
    'standard 7': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts',
        'Life Skills', 'Science & Technology', 'Agriculture', 'Social Studies'
    ],
    'standard 8': [
        'English', 'Mathematics', 'Chichewa', 'Bible Knowledge', 'Expressive Arts',
        'Life Skills', 'Science & Technology', 'Agriculture', 'Social Studies'
    ],
}

subjects_ref = db.collection('schools').document(school_id).collection('subjects')

# Clear existing and reload
for doc in subjects_ref.stream():
    doc.reference.delete()

for class_name, subjects in DEFAULT_SUBJECTS.items():
    subjects_ref.document(class_name).set({'subjects': subjects})
    print(f"Loaded {len(subjects)} subjects for {class_name}")

print("\nDone! All subjects loaded successfully.")
