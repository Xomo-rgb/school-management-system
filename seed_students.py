"""
Seed script — inserts 5 dummy students per class (50 total).
Run once from the project root:  python seed_students.py
"""
from app import app
from datetime import datetime

STUDENTS = [
    # --- Nursery (born ~2021) ---
    {"student_number":"HS-901","first_name":"Chisomo","middle_name":"Joy","last_name":"Banda","gender":"female","class_name":"nursery","dob":"2021-03-14","enrollment_date":"2024-01-08","guardian_name":"Alice Banda","guardian_contact":"0881234567","address":"Area 18, Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-902","first_name":"Kondwani","middle_name":"","last_name":"Phiri","gender":"male","class_name":"nursery","dob":"2021-07-22","enrollment_date":"2024-01-08","guardian_name":"James Phiri","guardian_contact":"0991234568","address":"Ndirande, Blantyre","status":"active","special_needs":""},
    {"student_number":"HS-903","first_name":"Pempho","middle_name":"Grace","last_name":"Mwale","gender":"female","class_name":"nursery","dob":"2020-11-05","enrollment_date":"2024-01-08","guardian_name":"Ruth Mwale","guardian_contact":"0881234569","address":"Chilomoni, Blantyre","status":"active","special_needs":""},
    {"student_number":"HS-904","first_name":"Takondwa","middle_name":"","last_name":"Tembo","gender":"male","class_name":"nursery","dob":"2021-01-30","enrollment_date":"2024-01-08","guardian_name":"Peter Tembo","guardian_contact":"0991234570","address":"Area 25, Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-905","first_name":"Alinafe","middle_name":"Hope","last_name":"Gondwe","gender":"female","class_name":"nursery","dob":"2021-09-18","enrollment_date":"2024-01-08","guardian_name":"Susan Gondwe","guardian_contact":"0881234571","address":"Limbe, Blantyre","status":"active","special_needs":""},
    # --- Reception (born ~2020) ---
    {"student_number":"HS-906","first_name":"Mphatso","middle_name":"","last_name":"Lungu","gender":"male","class_name":"reception","dob":"2020-04-11","enrollment_date":"2024-01-08","guardian_name":"Frank Lungu","guardian_contact":"0991234572","address":"Mzuzu, Northern Region","status":"active","special_needs":""},
    {"student_number":"HS-907","first_name":"Thandiwe","middle_name":"Faith","last_name":"Mkandawire","gender":"female","class_name":"reception","dob":"2020-08-27","enrollment_date":"2024-01-08","guardian_name":"Grace Mkandawire","guardian_contact":"0881234573","address":"Area 3, Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-908","first_name":"Blessings","middle_name":"","last_name":"Nyirenda","gender":"male","class_name":"reception","dob":"2020-02-15","enrollment_date":"2024-01-08","guardian_name":"Mary Nyirenda","guardian_contact":"0991234574","address":"Mchinji","status":"active","special_needs":""},
    {"student_number":"HS-909","first_name":"Fyness","middle_name":"Mercy","last_name":"Chavula","gender":"female","class_name":"reception","dob":"2019-12-03","enrollment_date":"2024-01-08","guardian_name":"David Chavula","guardian_contact":"0881234575","address":"Zomba","status":"active","special_needs":""},
    {"student_number":"HS-910","first_name":"Limbikani","middle_name":"","last_name":"Jere","gender":"male","class_name":"reception","dob":"2020-06-19","enrollment_date":"2024-01-08","guardian_name":"Anna Jere","guardian_contact":"0991234576","address":"Kasungu","status":"active","special_needs":""},
    # --- Standard 1 (born ~2019) ---
    {"student_number":"HS-911","first_name":"Dalitso","middle_name":"","last_name":"Mbewe","gender":"male","class_name":"standard 1","dob":"2019-03-08","enrollment_date":"2023-01-09","guardian_name":"Paul Mbewe","guardian_contact":"0881234577","address":"Nkhotakota","status":"active","special_needs":""},
    {"student_number":"HS-912","first_name":"Tiyamike","middle_name":"Rose","last_name":"Banda","gender":"female","class_name":"standard 1","dob":"2019-07-14","enrollment_date":"2023-01-09","guardian_name":"Joseph Banda","guardian_contact":"0991234578","address":"Area 12, Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-913","first_name":"Emmanuel","middle_name":"","last_name":"Phiri","gender":"male","class_name":"standard 1","dob":"2018-11-25","enrollment_date":"2023-01-09","guardian_name":"Helen Phiri","guardian_contact":"0881234579","address":"Bangwe, Blantyre","status":"active","special_needs":""},
    {"student_number":"HS-914","first_name":"Lindiwe","middle_name":"Star","last_name":"Kamwendo","gender":"female","class_name":"standard 1","dob":"2019-05-02","enrollment_date":"2023-01-09","guardian_name":"Samuel Kamwendo","guardian_contact":"0991234580","address":"Salima","status":"active","special_needs":""},
    {"student_number":"HS-915","first_name":"Yankho","middle_name":"","last_name":"Dzimbiri","gender":"male","class_name":"standard 1","dob":"2019-09-30","enrollment_date":"2023-01-09","guardian_name":"Violet Dzimbiri","guardian_contact":"0881234581","address":"Dedza","status":"active","special_needs":""},
    # --- Standard 2 (born ~2018) ---
    {"student_number":"HS-916","first_name":"Mercy","middle_name":"","last_name":"Zulu","gender":"female","class_name":"standard 2","dob":"2018-01-17","enrollment_date":"2022-01-10","guardian_name":"Charles Zulu","guardian_contact":"0991234582","address":"Lilongwe City","status":"active","special_needs":""},
    {"student_number":"HS-917","first_name":"Mavuto","middle_name":"","last_name":"Mhango","gender":"male","class_name":"standard 2","dob":"2018-06-23","enrollment_date":"2022-01-10","guardian_name":"Patricia Mhango","guardian_contact":"0881234583","address":"Mzimba","status":"active","special_needs":""},
    {"student_number":"HS-918","first_name":"Grace","middle_name":"Pemba","last_name":"Chirwa","gender":"female","class_name":"standard 2","dob":"2017-10-09","enrollment_date":"2022-01-10","guardian_name":"Robert Chirwa","guardian_contact":"0991234584","address":"Ntchisi","status":"active","special_needs":""},
    {"student_number":"HS-919","first_name":"James","middle_name":"","last_name":"Kumwenda","gender":"male","class_name":"standard 2","dob":"2018-04-28","enrollment_date":"2022-01-10","guardian_name":"Esther Kumwenda","guardian_contact":"0881234585","address":"Rumphi","status":"active","special_needs":""},
    {"student_number":"HS-920","first_name":"Amina","middle_name":"Stella","last_name":"Msowoya","gender":"female","class_name":"standard 2","dob":"2018-08-12","enrollment_date":"2022-01-10","guardian_name":"Hassan Msowoya","guardian_contact":"0991234586","address":"Karonga","status":"active","special_needs":""},
    # --- Standard 3 (born ~2017) ---
    {"student_number":"HS-921","first_name":"Chimwemwe","middle_name":"","last_name":"Tembo","gender":"male","class_name":"standard 3","dob":"2017-02-14","enrollment_date":"2021-01-11","guardian_name":"Dorothy Tembo","guardian_contact":"0881234587","address":"Mulanje","status":"active","special_needs":""},
    {"student_number":"HS-922","first_name":"Faith","middle_name":"","last_name":"Banda","gender":"female","class_name":"standard 3","dob":"2017-08-05","enrollment_date":"2021-01-11","guardian_name":"Thomas Banda","guardian_contact":"0991234588","address":"Phalombe","status":"active","special_needs":""},
    {"student_number":"HS-923","first_name":"David","middle_name":"Kondwani","last_name":"Nkosi","gender":"male","class_name":"standard 3","dob":"2016-12-20","enrollment_date":"2021-01-11","guardian_name":"Agnes Nkosi","guardian_contact":"0881234589","address":"Thyolo","status":"active","special_needs":""},
    {"student_number":"HS-924","first_name":"Memory","middle_name":"","last_name":"Chilombo","gender":"female","class_name":"standard 3","dob":"2017-05-16","enrollment_date":"2021-01-11","guardian_name":"George Chilombo","guardian_contact":"0991234590","address":"Chiradzulu","status":"active","special_needs":""},
    {"student_number":"HS-925","first_name":"Peter","middle_name":"","last_name":"Phiri","gender":"male","class_name":"standard 3","dob":"2017-10-01","enrollment_date":"2021-01-11","guardian_name":"Jane Phiri","guardian_contact":"0881234591","address":"Blantyre CBD","status":"active","special_needs":""},
    # --- Standard 4 (born ~2016) ---
    {"student_number":"HS-926","first_name":"Happiness","middle_name":"","last_name":"Gondwe","gender":"female","class_name":"standard 4","dob":"2015-11-07","enrollment_date":"2020-01-13","guardian_name":"Victor Gondwe","guardian_contact":"0991234592","address":"Dowa","status":"active","special_needs":""},
    {"student_number":"HS-927","first_name":"Michael","middle_name":"Dalitso","last_name":"Lungu","gender":"male","class_name":"standard 4","dob":"2016-03-24","enrollment_date":"2020-01-13","guardian_name":"Beatrice Lungu","guardian_contact":"0881234593","address":"Ntcheu","status":"active","special_needs":""},
    {"student_number":"HS-928","first_name":"Annie","middle_name":"","last_name":"Mwale","gender":"female","class_name":"standard 4","dob":"2016-07-18","enrollment_date":"2020-01-13","guardian_name":"Andrew Mwale","guardian_contact":"0991234594","address":"Balaka","status":"active","special_needs":""},
    {"student_number":"HS-929","first_name":"Charles","middle_name":"","last_name":"Nyirenda","gender":"male","class_name":"standard 4","dob":"2015-09-13","enrollment_date":"2020-01-13","guardian_name":"Joyce Nyirenda","guardian_contact":"0881234595","address":"Neno","status":"active","special_needs":""},
    {"student_number":"HS-930","first_name":"Stella","middle_name":"Alinafe","last_name":"Chavula","gender":"female","class_name":"standard 4","dob":"2016-01-30","enrollment_date":"2020-01-13","guardian_name":"Isaac Chavula","guardian_contact":"0991234596","address":"Machinga","status":"active","special_needs":""},
    # --- Standard 5 (born ~2015) ---
    {"student_number":"HS-931","first_name":"John","middle_name":"","last_name":"Jere","gender":"male","class_name":"standard 5","dob":"2014-10-04","enrollment_date":"2019-01-14","guardian_name":"Christina Jere","guardian_contact":"0881234597","address":"Mangochi","status":"active","special_needs":""},
    {"student_number":"HS-932","first_name":"Yolande","middle_name":"Tiyamike","last_name":"Mbewe","gender":"female","class_name":"standard 5","dob":"2015-02-19","enrollment_date":"2019-01-14","guardian_name":"Henry Mbewe","guardian_contact":"0991234598","address":"Lilongwe South","status":"active","special_needs":""},
    {"student_number":"HS-933","first_name":"Robert","middle_name":"","last_name":"Banda","gender":"male","class_name":"standard 5","dob":"2015-06-11","enrollment_date":"2019-01-14","guardian_name":"Miriam Banda","guardian_contact":"0881234599","address":"Area 36, Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-934","first_name":"Tamara","middle_name":"","last_name":"Kamwendo","gender":"female","class_name":"standard 5","dob":"2014-12-27","enrollment_date":"2019-01-14","guardian_name":"Richard Kamwendo","guardian_contact":"0991234600","address":"Mchinji","status":"active","special_needs":""},
    {"student_number":"HS-935","first_name":"Wisdom","middle_name":"Mphatso","last_name":"Dzimbiri","gender":"male","class_name":"standard 5","dob":"2015-08-23","enrollment_date":"2019-01-14","guardian_name":"Lydia Dzimbiri","guardian_contact":"0881234601","address":"Kasungu","status":"active","special_needs":""},
    # --- Standard 6 (born ~2014) ---
    {"student_number":"HS-936","first_name":"Patricia","middle_name":"","last_name":"Zulu","gender":"female","class_name":"standard 6","dob":"2013-07-09","enrollment_date":"2018-01-08","guardian_name":"Daniel Zulu","guardian_contact":"0991234602","address":"Nkhotakota","status":"active","special_needs":""},
    {"student_number":"HS-937","first_name":"Samuel","middle_name":"","last_name":"Mhango","gender":"male","class_name":"standard 6","dob":"2014-03-15","enrollment_date":"2018-01-08","guardian_name":"Florence Mhango","guardian_contact":"0881234603","address":"Mzimba","status":"active","special_needs":""},
    {"student_number":"HS-938","first_name":"Rose","middle_name":"Thandiwe","last_name":"Chirwa","gender":"female","class_name":"standard 6","dob":"2013-11-28","enrollment_date":"2018-01-08","guardian_name":"Kenneth Chirwa","guardian_contact":"0991234604","address":"Dedza","status":"active","special_needs":""},
    {"student_number":"HS-939","first_name":"Pemba","middle_name":"","last_name":"Kumwenda","gender":"male","class_name":"standard 6","dob":"2014-08-07","enrollment_date":"2018-01-08","guardian_name":"Edith Kumwenda","guardian_contact":"0881234605","address":"Salima","status":"active","special_needs":""},
    {"student_number":"HS-940","first_name":"Hope","middle_name":"","last_name":"Msowoya","gender":"female","class_name":"standard 6","dob":"2013-04-21","enrollment_date":"2018-01-08","guardian_name":"Frank Msowoya","guardian_contact":"0991234606","address":"Zomba","status":"active","special_needs":""},
    # --- Standard 7 (born ~2013) ---
    {"student_number":"HS-941","first_name":"Chimwemwe","middle_name":"John","last_name":"Nkosi","gender":"male","class_name":"standard 7","dob":"2012-09-16","enrollment_date":"2017-01-09","guardian_name":"Prisca Nkosi","guardian_contact":"0881234607","address":"Karonga","status":"active","special_needs":""},
    {"student_number":"HS-942","first_name":"Charity","middle_name":"","last_name":"Chilombo","gender":"female","class_name":"standard 7","dob":"2013-01-04","enrollment_date":"2017-01-09","guardian_name":"Moses Chilombo","guardian_contact":"0991234608","address":"Rumphi","status":"active","special_needs":""},
    {"student_number":"HS-943","first_name":"Blessings","middle_name":"Mavuto","last_name":"Phiri","gender":"male","class_name":"standard 7","dob":"2012-05-30","enrollment_date":"2017-01-09","guardian_name":"Clara Phiri","guardian_contact":"0881234609","address":"Blantyre","status":"active","special_needs":""},
    {"student_number":"HS-944","first_name":"Lindiwe","middle_name":"","last_name":"Banda","gender":"female","class_name":"standard 7","dob":"2013-10-12","enrollment_date":"2017-01-09","guardian_name":"Stephen Banda","guardian_contact":"0991234610","address":"Lilongwe","status":"active","special_needs":""},
    {"student_number":"HS-945","first_name":"Kondwani","middle_name":"","last_name":"Gondwe","gender":"male","class_name":"standard 7","dob":"2012-12-25","enrollment_date":"2017-01-09","guardian_name":"Agness Gondwe","guardian_contact":"0881234611","address":"Ntchisi","status":"active","special_needs":""},
    # --- Standard 8 (born ~2012) ---
    {"student_number":"HS-946","first_name":"Fyness","middle_name":"","last_name":"Lungu","gender":"female","class_name":"standard 8","dob":"2011-08-03","enrollment_date":"2016-01-11","guardian_name":"Arnold Lungu","guardian_contact":"0991234612","address":"Mulanje","status":"active","special_needs":""},
    {"student_number":"HS-947","first_name":"Dalitso","middle_name":"James","last_name":"Mkandawire","gender":"male","class_name":"standard 8","dob":"2012-02-17","enrollment_date":"2016-01-11","guardian_name":"Veronica Mkandawire","guardian_contact":"0881234613","address":"Thyolo","status":"active","special_needs":""},
    {"student_number":"HS-948","first_name":"Tiyamike","middle_name":"","last_name":"Nyirenda","gender":"female","class_name":"standard 8","dob":"2011-06-08","enrollment_date":"2016-01-11","guardian_name":"Leonard Nyirenda","guardian_contact":"0991234614","address":"Chiradzulu","status":"active","special_needs":""},
    {"student_number":"HS-949","first_name":"Takondwa","middle_name":"Emmanuel","last_name":"Mwale","gender":"male","class_name":"standard 8","dob":"2012-10-22","enrollment_date":"2016-01-11","guardian_name":"Felicity Mwale","guardian_contact":"0881234615","address":"Phalombe","status":"active","special_needs":""},
    {"student_number":"HS-950","first_name":"Alinafe","middle_name":"","last_name":"Tembo","gender":"female","class_name":"standard 8","dob":"2011-04-14","enrollment_date":"2016-01-11","guardian_name":"Winston Tembo","guardian_contact":"0991234616","address":"Balaka","status":"active","special_needs":""},
]

def run():
    with app.test_request_context('/'):
        from firebase_helpers import add_document

        added = 0
        for s in STUDENTS:
            data = {
                'first_name':      s['first_name'],
                'middle_name':     s['middle_name'],
                'last_name':       s['last_name'],
                'student_number':  s['student_number'],
                'gender':          s['gender'],
                'class_name':      s['class_name'],
                'dob':             datetime.strptime(s['dob'], '%Y-%m-%d'),
                'enrollment_date': datetime.strptime(s['enrollment_date'], '%Y-%m-%d'),
                'guardian_name':   s['guardian_name'],
                'guardian_contact': s['guardian_contact'],
                'address':         s['address'],
                'status':          s['status'],
                'special_needs':   s['special_needs'],
            }
            add_document('students', data)
            added += 1
            print(f"[{added:02d}/50] Added  {s['student_number']}  {s['first_name']} {s['last_name']}  ({s['class_name']})")

        print(f"\nDone — {added} students added.")

if __name__ == '__main__':
    run()
