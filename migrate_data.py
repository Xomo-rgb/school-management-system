"""
Data Migration Script: PostgreSQL (Supabase) to Firebase Firestore

This script exports your existing data from PostgreSQL and imports it into Firebase.
Run this AFTER setting up Firebase credentials.

Usage:
    python migrate_data.py
"""

import psycopg2
import psycopg2.extras
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime

# Load environment variables if .env file exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# PostgreSQL connection (from your current setup)
def get_pg_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME"),
        sslmode='require'
    )

# Initialize Firebase
def init_firebase():
    cred_path = 'firebase-credentials.json'
    if not os.path.exists(cred_path):
        print("ERROR: firebase-credentials.json not found!")
        print("Please download it from Firebase Console and place it in project root.")
        exit(1)
    
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    return firestore.client()

def migrate_users(pg_conn, db, school_id):
    """Migrate users table"""
    print("Migrating users...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.users")
    users = cursor.fetchall()
    
    users_ref = db.collection('schools').document(school_id).collection('users')
    count = 0
    for user in users:
        user_data = dict(user)
        user_id = str(user_data.pop('user_id'))
        users_ref.document(user_id).set(user_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} users")

def migrate_students(pg_conn, db, school_id):
    """Migrate students table"""
    print("Migrating students...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.students")
    students = cursor.fetchall()
    
    students_ref = db.collection('schools').document(school_id).collection('students')
    count = 0
    for student in students:
        student_data = dict(student)
        student_id = str(student_data.pop('student_id'))
        
        # Convert dates to datetime objects
        if student_data.get('dob'):
            student_data['dob'] = datetime.combine(student_data['dob'], datetime.min.time())
        if student_data.get('enrollment_date'):
            student_data['enrollment_date'] = datetime.combine(student_data['enrollment_date'], datetime.min.time())
        
        students_ref.document(student_id).set(student_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} students")

def migrate_fee_payments(pg_conn, db, school_id):
    """Migrate fee_payments table"""
    print("Migrating fee payments...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.fee_payments")
    payments = cursor.fetchall()
    
    payments_ref = db.collection('schools').document(school_id).collection('fee_payments')
    count = 0
    for payment in payments:
        payment_data = dict(payment)
        payment_id = str(payment_data.pop('payment_id'))
        
        # Convert student_id to string for reference
        payment_data['student_id'] = str(payment_data['student_id'])
        
        # Convert date to datetime
        if payment_data.get('payment_date'):
            payment_data['payment_date'] = datetime.combine(payment_data['payment_date'], datetime.min.time())
        
        payments_ref.document(payment_id).set(payment_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} fee payments")

def migrate_classes(pg_conn, db, school_id):
    """Migrate classes table"""
    print("Migrating classes...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.classes")
    classes = cursor.fetchall()
    
    classes_ref = db.collection('schools').document(school_id).collection('classes')
    count = 0
    for cls in classes:
        class_data = dict(cls)
        class_id = str(class_data.pop('class_id'))
        classes_ref.document(class_id).set(class_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} classes")

def migrate_exam_results(pg_conn, db, school_id):
    """Migrate exam_results table"""
    print("Migrating exam results...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.exam_results")
    results = cursor.fetchall()
    
    results_ref = db.collection('schools').document(school_id).collection('exam_results')
    count = 0
    for result in results:
        result_data = dict(result)
        result_id = str(result_data.pop('result_id'))
        result_data['student_id'] = str(result_data['student_id'])
        results_ref.document(result_id).set(result_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} exam results")

def migrate_activity_logs(pg_conn, db, school_id):
    """Migrate activity_logs table"""
    print("Migrating activity logs...")
    cursor = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute("SELECT * FROM public.activity_logs ORDER BY timestamp DESC LIMIT 1000")  # Last 1000 logs
    logs = cursor.fetchall()
    
    logs_ref = db.collection('schools').document(school_id).collection('activity_logs')
    count = 0
    for log in logs:
        log_data = dict(log)
        log_id = str(log_data.pop('log_id'))
        
        # Convert timestamp
        if log_data.get('timestamp'):
            log_data['timestamp'] = log_data['timestamp']
        
        logs_ref.document(log_id).set(log_data)
        count += 1
    
    cursor.close()
    print(f"✓ Migrated {count} activity logs")

def main():
    print("=" * 60)
    print("PostgreSQL to Firebase Migration Script")
    print("=" * 60)
    
    school_id = input("Enter school ID (default: default_school): ").strip() or "default_school"
    
    print("\nConnecting to PostgreSQL...")
    pg_conn = get_pg_connection()
    print("✓ Connected to PostgreSQL")
    
    print("\nInitializing Firebase...")
    db = init_firebase()
    print("✓ Connected to Firebase")
    
    print(f"\nMigrating data to school: {school_id}")
    print("-" * 60)
    
    try:
        migrate_users(pg_conn, db, school_id)
        migrate_students(pg_conn, db, school_id)
        migrate_classes(pg_conn, db, school_id)
        migrate_fee_payments(pg_conn, db, school_id)
        migrate_exam_results(pg_conn, db, school_id)
        migrate_activity_logs(pg_conn, db, school_id)
        
        print("-" * 60)
        print("✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Verify data in Firebase Console")
        print("2. Replace old route files with Firebase versions")
        print("3. Test the application thoroughly")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pg_conn.close()

if __name__ == "__main__":
    main()
