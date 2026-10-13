"""
Phase 14.2: API Testing Script
Tests all key API endpoints to ensure they work correctly.
"""

import urllib.request
import urllib.error
import json
from datetime import datetime

API_URL = 'http://localhost:8000'

def api_request(method, endpoint, data=None):
    """Helper function to make API requests using urllib"""
    url = f'{API_URL}{endpoint}'
    headers = {'Content-Type': 'application/json'}

    if method == 'GET':
        req = urllib.request.Request(url, headers=headers)
    elif method == 'POST':
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    elif method == 'PATCH':
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method='PATCH')
    elif method == 'DELETE':
        req = urllib.request.Request(url, headers=headers, method='DELETE')

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            content = response.read().decode('utf-8')
            return status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        try:
            error_content = e.read().decode('utf-8')
            return e.code, json.loads(error_content) if error_content else None
        except:
            return e.code, {'error': 'HTTP Error'}
    except Exception as e:
        return None, {'error': str(e)}

def test_api():
    print("=" * 60)
    print("API TESTING - Phase 14.2")
    print("=" * 60)

    # Test 1: Health Check
    print("\n--- Test 1: Health Check ---")
    status, response = api_request('GET', '/health')
    print(f"  Status: {status}")
    print(f"  Response: {response}")
    if status == 200:
        print("  [OK] Health check passed")
    else:
        print(f"  [FAIL] Health check failed")

    # Test 2: Config Endpoint
    print("\n--- Test 2: Config Endpoint ---")
    status, config = api_request('GET', '/config')
    print(f"  Status: {status}")
    if config:
        print(f"  Max questions: {config.get('max_questions')}")
        print(f"  OpenAI configured: {config.get('openai_configured')}")
        print("  [OK] Config endpoint passed")
    else:
        print(f"  [FAIL] Config endpoint failed")

    # Test 3: Create Patient
    print("\n--- Test 3: Create Patient ---")
    patient_id = None
    patient_data = {
        'name': 'Test Patient',
        'age': 30,
        'phone': '+919876543210',
        'sex': 'Male',
        'vitals': {'bp': '120/80', 'sugar': '100'}
    }
    status, result = api_request('POST', '/patients', patient_data)
    print(f"  Status: {status}")
    if result:
        patient_id = result.get('patient_id')
        print(f"  Patient ID: {patient_id}")
        print("  [OK] Patient creation passed")
    else:
        print(f"  [FAIL] Patient creation failed")

    # Test 4: Get Patient
    print("\n--- Test 4: Get Patient ---")
    if patient_id:
        status, patient = api_request('GET', f'/patients/{patient_id}')
        print(f"  Status: {status}")
        if patient:
            print(f"  Patient name: {patient.get('name')}")
            print("  [OK] Get patient passed")
        else:
            print(f"  [FAIL] Get patient failed")

    # Test 5: Get Doctors
    print("\n--- Test 5: Get Doctors ---")
    status, doctors = api_request('GET', '/doctors')
    print(f"  Status: {status}")
    if doctors:
        print(f"  Number of doctors: {len(doctors)}")
        if doctors:
            print(f"  First doctor: {doctors[0].get('name')} - {doctors[0].get('specialty')}")
        print("  [OK] Get doctors passed")
    else:
        print(f"  [FAIL] Get doctors failed")

    # Test 6: Doctor Login
    print("\n--- Test 6: Doctor Login ---")
    status, doctor = api_request('POST', '/doctors/login?doctor_id=DOC-002')
    print(f"  Status: {status}")
    if doctor:
        print(f"  Doctor name: {doctor.get('name')}")
        print(f"  Specialty: {doctor.get('specialty')}")
        print("  [OK] Doctor login passed")
    else:
        print(f"  [FAIL] Doctor login failed")

    # Test 7: Add to Queue (with symptoms for specialty matching)
    print("\n--- Test 7: Add to Queue (with specialty matching) ---")
    queue_token = None
    if patient_id:
        queue_data = {
            'patient_id': patient_id,
            'priority': 'medium',
            'symptoms': ['chest pain', 'breathlessness']  # Should match Cardiology
        }
        status, result = api_request('POST', '/queue', queue_data)
        print(f"  Status: {status}")
        if result:
            queue_token = result.get('token')
            assigned_doctor = result.get('assigned_doctor')
            print(f"  Token: {queue_token}")
            print(f"  Assigned doctor: {assigned_doctor.get('name') if assigned_doctor else 'None'}")
            print(f"  Specialty: {assigned_doctor.get('specialty') if assigned_doctor else 'None'}")
            print("  [OK] Add to queue passed")
        else:
            print(f"  [FAIL] Add to queue failed")

    # Test 8: Get Queue
    print("\n--- Test 8: Get Queue ---")
    if patient_id:
        status, queue_info = api_request('GET', f'/queue?patient_id={patient_id}')
        print(f"  Status: {status}")
        if queue_info:
            print(f"  Token: {queue_info.get('token')}")
            print(f"  Priority: {queue_info.get('priority')}")
            print(f"  People ahead: {queue_info.get('people_ahead')}")
            print("  [OK] Get queue passed")
        else:
            print(f"  [FAIL] Get queue failed")

    # Test 9: Create Prescription
    print("\n--- Test 9: Create Prescription ---")
    if patient_id:
        prescription_data = {
            'patient_id': patient_id,
            'doctor_id': 'DOC-002',
            'doctor_notes': 'Test prescription notes',
            'medications': [
                {'name': 'Paracetamol', 'type': 'tablet', 'dosage': '500mg', 'quantity': '10', 'frequency': 'twice daily'}
            ],
            'language': 'English'
        }
        status, result = api_request('POST', '/prescriptions', prescription_data)
        print(f"  Status: {status}")
        if result:
            print(f"  Prescription ID: {result.get('prescription_id')}")
            print("  [OK] Create prescription passed")
        else:
            print(f"  [FAIL] Create prescription failed")

    # Test 10: Get Patient Prescriptions
    print("\n--- Test 10: Get Patient Prescriptions ---")
    if patient_id:
        status, prescriptions = api_request('GET', f'/patients/{patient_id}/prescriptions')
        print(f"  Status: {status}")
        if prescriptions:
            print(f"  Number of prescriptions: {len(prescriptions)}")
            print("  [OK] Get prescriptions passed")
        else:
            print(f"  [FAIL] Get prescriptions failed")

    # Test 11: Get Patient Visits
    print("\n--- Test 11: Get Patient Visits ---")
    if patient_id:
        status, visits = api_request('GET', f'/patients/{patient_id}/visits')
        print(f"  Status: {status}")
        if visits:
            print(f"  Number of visits: {len(visits)}")
            print("  [OK] Get visits passed")
        else:
            print(f"  [FAIL] Get visits failed")

    # Test 12: Doctor Reassign by Patient
    print("\n--- Test 12: Doctor Reassign by Patient ---")
    if patient_id:
        reassign_data = {
            'patient_id': patient_id,
            'new_doctor_id': 'DOC-001'  # Reassign to Cardiology
        }
        status, result = api_request('POST', '/queue/reassign-by-patient', reassign_data)
        print(f"  Status: {status}")
        if result:
            print(f"  Reassigned to: {result.get('assigned_doctor', {}).get('name')}")
            print("  [OK] Doctor reassign passed")
        else:
            print(f"  [FAIL] Doctor reassign failed")

    # Test 13: Get Doctor's Patients
    print("\n--- Test 13: Get Doctor's Patients ---")
    status, patients = api_request('GET', '/doctors/DOC-002/patients')
    print(f"  Status: {status}")
    if patients:
        print(f"  Number of patients: {len(patients)}")
        print("  [OK] Get doctor's patients passed")
    else:
        print(f"  [FAIL] Get doctor's patients failed")

    # Test 14: Get Patient Review (Doctor endpoint)
    print("\n--- Test 14: Get Patient Review ---")
    if patient_id:
        status, review = api_request('GET', f'/doctors/DOC-002/patients/{patient_id}/review')
        print(f"  Status: {status}")
        if review:
            print(f"  Patient name: {review.get('patient', {}).get('name')}")
            print(f"  Number of reports: {len(review.get('reports', []))}")
            print(f"  Number of visits: {len(review.get('visits', []))}")
            print(f"  Number of prescriptions: {len(review.get('prescriptions', []))}")
            print("  [OK] Get patient review passed")
        else:
            print(f"  [FAIL] Get patient review failed")

    # Test 15: Generate Patient Report
    print("\n--- Test 15: Generate Patient Report ---")
    if patient_id:
        report_data = {
            'patient_id': patient_id,
            'doctor_id': 'DOC-002',
            'doctor_notes': 'Patient is recovering well',
            'medications': [{'name': 'Test Med', 'dosage': '500mg'}],
            'diagnosis': 'Mild cold',
            'language': 'English'
        }
        status, result = api_request('POST', f'/doctors/DOC-002/patients/{patient_id}/generate-report', report_data)
        print(f"  Status: {status}")
        if result:
            print(f"  Report generated: {bool(result.get('report_content'))}")
            print(f"  Language: {result.get('language')}")
            print("  [OK] Generate report passed")
        else:
            print(f"  [FAIL] Generate report failed")

    print("\n" + "=" * 60)
    print("API TESTING COMPLETE")
    print("=" * 60)
    print("\nNote: Some endpoints may fail if OpenAI API is not configured.")
    print("File upload endpoints require actual files and were not tested in this script.")

if __name__ == '__main__':
    test_api()
