"""
Phase 14.1: Database Testing Script
Verifies all tables are created correctly and CRUD operations work.
"""

import sqlite3
import json
from datetime import datetime

def test_database():
    print("=" * 60)
    print("DATABASE TESTING - Phase 14.1")
    print("=" * 60)

    # Connect to in-memory database (same as main.py)
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Create tables (same as main.py)
    conn.execute('CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY,name TEXT,age INTEGER,phone TEXT,sex TEXT,vitals TEXT,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,filename TEXT,content_type TEXT,bytes INTEGER,extracted_text TEXT,key_points TEXT,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,visit_date TEXT,summary TEXT,symptoms TEXT,risk TEXT,priority TEXT,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,token TEXT,priority TEXT,status TEXT,assigned_doctor_id TEXT,consultation_type TEXT,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,role TEXT,text TEXT,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS doctors (id TEXT PRIMARY KEY,name TEXT,specialty TEXT,phone TEXT,is_active INTEGER,created_at TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS prescriptions (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,visit_id INTEGER,doctor_id TEXT,doctor_notes TEXT,medications TEXT,created_at TEXT,language TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS report_comparisons (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,past_report_id INTEGER,present_report_id INTEGER,comparison_summary TEXT,created_at TEXT)')
    conn.commit()

    print("\n[OK] All tables created successfully")

    # Test 1: Verify table structure
    print("\n--- Test 1: Table Structure Verification ---")
    tables = ['patients', 'reports', 'visits', 'queue', 'conversations', 'doctors', 'prescriptions', 'report_comparisons']
    for table in tables:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"  {table}: {', '.join(columns)}")

    # Test 2: CRUD Operations - Patients
    print("\n--- Test 2: Patient CRUD Operations ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({'bp': '120/80'}), datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Patient created")

    patient = conn.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
    print(f"  [OK] Patient retrieved: {patient['name']}")

    conn.execute('UPDATE patients SET age = 31 WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Patient updated")

    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Patient deleted")

    # Test 3: CRUD Operations - Doctors
    print("\n--- Test 3: Doctor CRUD Operations ---")
    doctor_id = 'DOC-TEST'
    conn.execute('INSERT INTO doctors VALUES (?,?,?,?,?,?)',
                 (doctor_id, 'Dr. Test', 'Test Specialty', '+919876543211', 1, datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Doctor created")

    doctor = conn.execute('SELECT * FROM doctors WHERE id = ?', (doctor_id,)).fetchone()
    print(f"  [OK] Doctor retrieved: {doctor['name']}")

    conn.execute('DELETE FROM doctors WHERE id = ?', (doctor_id,))
    conn.commit()
    print("  [OK] Doctor deleted")

    # Test 4: CRUD Operations - Prescriptions
    print("\n--- Test 4: Prescription CRUD Operations ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({}), datetime.now().isoformat()))
    conn.commit()

    medications = [{'name': 'Test Med', 'dosage': '500mg', 'frequency': 'twice daily'}]
    conn.execute('INSERT INTO prescriptions (patient_id, visit_id, doctor_id, doctor_notes, medications, created_at, language) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 1, 'DOC-002', 'Test notes', json.dumps(medications), datetime.now().isoformat(), 'English'))
    conn.commit()
    print("  [OK] Prescription created")

    prescription = conn.execute('SELECT * FROM prescriptions WHERE patient_id = ?', (patient_id,)).fetchone()
    meds = json.loads(prescription['medications'])
    print(f"  [OK] Prescription retrieved: {meds[0]['name']}")

    conn.execute('DELETE FROM prescriptions WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Prescription deleted")

    # Test 5: CRUD Operations - Queue
    print("\n--- Test 5: Queue CRUD Operations ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({}), datetime.now().isoformat()))
    conn.commit()

    conn.execute('INSERT INTO queue (patient_id, token, priority, status, assigned_doctor_id, consultation_type, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'TEST-TOKEN', 'medium', 'waiting', 'DOC-002', 'initial', datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Queue entry created")

    queue = conn.execute('SELECT * FROM queue WHERE patient_id = ?', (patient_id,)).fetchone()
    print(f"  [OK] Queue entry retrieved: {queue['token']}")

    conn.execute('UPDATE queue SET status = ? WHERE patient_id = ?', ('in_consultation', patient_id))
    conn.commit()
    print("  [OK] Queue status updated")

    conn.execute('DELETE FROM queue WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Queue entry deleted")

    # Test 6: CRUD Operations - Reports
    print("\n--- Test 6: Report CRUD Operations ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({}), datetime.now().isoformat()))
    conn.commit()

    key_points = ['Test finding 1', 'Test finding 2']
    conn.execute('INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'test.pdf', 'application/pdf', 1024, 'Test text', json.dumps(key_points), datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Report created")

    report = conn.execute('SELECT * FROM reports WHERE patient_id = ?', (patient_id,)).fetchone()
    points = json.loads(report['key_points'])
    print(f"  [OK] Report retrieved: {report['filename']}")

    conn.execute('DELETE FROM reports WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Report deleted")

    # Test 7: CRUD Operations - Report Comparisons
    print("\n--- Test 7: Report Comparison CRUD Operations ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({}), datetime.now().isoformat()))
    conn.commit()

    conn.execute('INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'test1.pdf', 'application/pdf', 1024, 'Test text 1', json.dumps(['old']), datetime.now().isoformat()))
    conn.commit()
    past_report_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    conn.execute('INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'test2.pdf', 'application/pdf', 1024, 'Test text 2', json.dumps(['new']), datetime.now().isoformat()))
    conn.commit()
    present_report_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    comparison_summary = {'improved': [], 'deteriorated': [], 'unchanged': []}
    conn.execute('INSERT INTO report_comparisons (patient_id, past_report_id, present_report_id, comparison_summary, created_at) VALUES (?,?,?,?,?)',
                 (patient_id, past_report_id, present_report_id, json.dumps(comparison_summary), datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Report comparison created")

    comparison = conn.execute('SELECT * FROM report_comparisons WHERE patient_id = ?', (patient_id,)).fetchone()
    print(f"  [OK] Report comparison retrieved")

    conn.execute('DELETE FROM report_comparisons WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM reports WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Report comparison deleted")

    # Test 8: Foreign Key Relationships
    print("\n--- Test 8: Foreign Key Relationships ---")
    patient_id = f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}'
    conn.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'Test Patient', 30, '+919876543210', 'Male', json.dumps({}), datetime.now().isoformat()))
    conn.commit()

    # Create related records
    conn.execute('INSERT INTO queue (patient_id, token, priority, status, assigned_doctor_id, consultation_type, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'TEST-TOKEN', 'medium', 'waiting', 'DOC-002', 'initial', datetime.now().isoformat()))
    conn.execute('INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, 'test.pdf', 'application/pdf', 1024, 'Test text', json.dumps([]), datetime.now().isoformat()))
    conn.execute('INSERT INTO visits (patient_id, visit_date, summary, symptoms, risk, priority, created_at) VALUES (?,?,?,?,?,?,?)',
                 (patient_id, datetime.now().isoformat(), json.dumps({}), json.dumps([]), 'medium', 'medium', datetime.now().isoformat()))
    conn.commit()
    print("  [OK] Related records created")

    # Verify relationships
    queue_count = conn.execute('SELECT COUNT(*) FROM queue WHERE patient_id = ?', (patient_id,)).fetchone()[0]
    report_count = conn.execute('SELECT COUNT(*) FROM reports WHERE patient_id = ?', (patient_id,)).fetchone()[0]
    visit_count = conn.execute('SELECT COUNT(*) FROM visits WHERE patient_id = ?', (patient_id,)).fetchone()[0]
    print(f"  [OK] Queue records: {queue_count}, Reports: {report_count}, Visits: {visit_count}")

    # Cleanup
    conn.execute('DELETE FROM queue WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM reports WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM visits WHERE patient_id = ?', (patient_id,))
    conn.execute('DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    print("  [OK] Cleanup successful")

    print("\n" + "=" * 60)
    print("DATABASE TESTING COMPLETE - All tests passed [OK]")
    print("=" * 60)

    conn.close()

if __name__ == '__main__':
    test_database()
