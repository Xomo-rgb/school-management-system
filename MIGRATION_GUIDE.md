# Firebase Migration Guide

## ✅ Files Created:
1. `firebase_setup.md` - Firebase setup instructions
2. `firebase_db.py` - New database layer for Firebase
3. `routes/auth_firebase.py` - Migrated auth route (example)
4. `utils_firebase.py` - Migrated utilities
5. `migrate_data.py` - Data migration script

## 📋 Migration Steps:

### Step 1: Setup Firebase (15 minutes)
Follow instructions in `firebase_setup.md`:
- Create Firebase project
- Enable Firestore
- Download credentials JSON
- Install firebase-admin

```bash
pip install -r requirements.txt
```

### Step 2: Migrate Your Data (5 minutes)
Run the migration script to copy data from PostgreSQL to Firebase:

```bash
python migrate_data.py
```

This will copy:
- Users
- Students  
- Classes
- Fee payments
- Exam results
- Activity logs

### Step 3: Replace Route Files (One at a time)

I've created Firebase versions of your files. Replace them one by one:

**Start with auth (already done):**
```bash
# Backup old file
copy routes\auth.py routes\auth_old.py

# Replace with Firebase version
copy routes\auth_firebase.py routes\auth.py
```

**Then utils:**
```bash
copy utils.py utils_old.py
copy utils_firebase.py utils.py
```

### Step 4: Test Login
Start your app and test login:
```bash
python app.py
```

### Step 5: Migrate Remaining Routes

I'll help you migrate these files one by one:
- ✅ auth.py (DONE - example provided)
- ⏳ student.py
- ⏳ admin.py  
- ⏳ teacher.py
- ⏳ user.py
- ⏳ assignment.py
- ⏳ curriculum.py
- ⏳ profile.py

## 🔄 Firebase Query Patterns

### PostgreSQL → Firebase Translation:

**SELECT with WHERE:**
```python
# OLD (PostgreSQL)
cursor.execute("SELECT * FROM students WHERE class_name = %s", (class_name,))

# NEW (Firebase)
db.collection('schools').document(school_id).collection('students')\
  .where('class_name', '==', class_name).stream()
```

**INSERT:**
```python
# OLD
cursor.execute("INSERT INTO students (...) VALUES (...)")

# NEW
db.collection('schools').document(school_id).collection('students').add({...})
```

**UPDATE:**
```python
# OLD
cursor.execute("UPDATE students SET ... WHERE student_id = %s")

# NEW
db.collection('schools').document(school_id).collection('students')\
  .document(student_id).update({...})
```

**DELETE:**
```python
# OLD
cursor.execute("DELETE FROM students WHERE student_id = %s")

# NEW
db.collection('schools').document(school_id).collection('students')\
  .document(student_id).delete()
```

**COUNT:**
```python
# OLD
cursor.execute("SELECT COUNT(*) FROM students")

# NEW
len(list(db.collection('schools').document(school_id).collection('students').stream()))
```

## 🎯 Next Steps:

1. Complete Firebase setup
2. Run data migration
3. Test auth login
4. Let me know which route to migrate next!

Would you like me to migrate another route file? Just tell me which one!
