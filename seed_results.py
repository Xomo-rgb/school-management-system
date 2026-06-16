"""
Seed script — inserts random exam results for the 50 dummy students (HS-901..HS-950).
Scores are varied: some students are strong, some average, some failing.
Run once:  python seed_results.py
"""
import random
from app import app

# Default subjects per class level (used if not configured in Firebase)
DEFAULT_SUBJECTS = {
    'nursery':    ['English', 'Mathematics', 'Environmental Studies', 'Creative Arts'],
    'reception':  ['English', 'Mathematics', 'Environmental Studies', 'Creative Arts'],
    'standard 1': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education'],
    'standard 2': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education'],
    'standard 3': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education'],
    'standard 4': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education'],
    'standard 5': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education', 'History', 'Geography'],
    'standard 6': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education', 'History', 'Geography'],
    'standard 7': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education', 'History', 'Geography'],
    'standard 8': ['English', 'Mathematics', 'Science', 'Social Studies', 'Chichewa', 'Religious Education', 'History', 'Geography'],
}

def score_for_profile(profile):
    """
    Generate a realistic score based on a student's profile band.
    profile: 'strong' | 'average' | 'weak' | 'failing'
    """
    if profile == 'strong':
        return random.randint(72, 98)
    elif profile == 'average':
        return random.randint(50, 74)
    elif profile == 'weak':
        return random.randint(35, 55)
    else:  # failing
        return random.randint(20, 42)

# HS-901 to HS-950 — assign a profile to each student number so results are consistent
STUDENT_PROFILES = {
    'HS-901': 'strong',  'HS-902': 'average', 'HS-903': 'average', 'HS-904': 'weak',    'HS-905': 'strong',
    'HS-906': 'failing', 'HS-907': 'average', 'HS-908': 'strong',  'HS-909': 'weak',    'HS-910': 'average',
    'HS-911': 'average', 'HS-912': 'strong',  'HS-913': 'failing', 'HS-914': 'average', 'HS-915': 'weak',
    'HS-916': 'strong',  'HS-917': 'average', 'HS-918': 'weak',    'HS-919': 'average', 'HS-920': 'failing',
    'HS-921': 'average', 'HS-922': 'strong',  'HS-923': 'weak',    'HS-924': 'average', 'HS-925': 'strong',
    'HS-926': 'failing', 'HS-927': 'average', 'HS-928': 'strong',  'HS-929': 'weak',    'HS-930': 'average',
    'HS-931': 'strong',  'HS-932': 'average', 'HS-933': 'failing', 'HS-934': 'strong',  'HS-935': 'weak',
    'HS-936': 'average', 'HS-937': 'strong',  'HS-938': 'average', 'HS-939': 'weak',    'HS-940': 'failing',
    'HS-941': 'strong',  'HS-942': 'average', 'HS-943': 'weak',    'HS-944': 'strong',  'HS-945': 'average',
    'HS-946': 'average', 'HS-947': 'strong',  'HS-948': 'failing', 'HS-949': 'average', 'HS-950': 'weak',
}

def run():
    random.seed(42)  # reproducible

    with app.test_request_context('/'):
        from firebase_db import get_firestore_db, get_school_id
        from academic_helpers import get_current_academic_period, get_subjects_for_class
        from firebase_helpers import add_document

        db        = get_firestore_db()
        school_id = get_school_id()

        # Get current academic period
        period = get_current_academic_period()
        term   = period.get('term', '')
        year   = period.get('year', '')

        if term == 'Not Set' or year == 'Not Set':
            print("ERROR: No active academic period found. Set one up in the system first.")
            return

        print(f"Inserting results for: {year} — {term}\n")

        # Fetch all students HS-901..HS-950
        students_ref = db.collection('schools').document(school_id).collection('students')
        all_students = [doc for doc in students_ref.stream()]

        target_numbers = set(STUDENT_PROFILES.keys())
        seed_students  = [
            {'id': doc.id, **doc.to_dict()}
            for doc in all_students
            if doc.to_dict().get('student_number') in target_numbers
        ]

        print(f"Found {len(seed_students)} seed students.\n")

        total_inserted = 0

        for student in seed_students:
            student_id  = student['id']
            student_no  = student.get('student_number', '')
            class_name  = student.get('class_name', '')
            profile     = STUDENT_PROFILES.get(student_no, 'average')

            # Get subjects — Firebase first, fall back to defaults
            subjects = get_subjects_for_class(class_name)
            if not subjects:
                subjects = DEFAULT_SUBJECTS.get(class_name, ['English', 'Mathematics', 'Science'])

            scores = []
            for subject in subjects:
                score = score_for_profile(profile)
                # small random variance per subject to avoid identical scores
                score = max(0, min(100, score + random.randint(-8, 8)))

                add_document('exam_results', {
                    'student_id':    student_id,
                    'class_name':    class_name,
                    'subject':       subject,
                    'term':          term,
                    'academic_year': year,
                    'final_score':   score,
                    'entered_by':    'seed_script',
                })
                scores.append(score)
                total_inserted += 1

            avg = round(sum(scores) / len(scores), 1)
            status = 'PASS' if avg >= 40 else 'FAIL'
            print(f"  {student_no}  {student.get('first_name')} {student.get('last_name'):<18}  "
                  f"({class_name:<12})  avg={avg:5.1f}%  [{status}]  profile={profile}")

        print(f"\nDone — {total_inserted} result records inserted across {len(seed_students)} students.")

if __name__ == '__main__':
    run()
