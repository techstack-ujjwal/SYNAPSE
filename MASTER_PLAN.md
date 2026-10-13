# MASTER PLAN - Synapse AI Enhancement
**Senior Software AI Engineer Design Document**

## Overview
This plan outlines the development of enhanced features for the Synapse AI hospital management system, including improved report analysis, patient dashboard, and a complete doctor portal with prescription management.

---

## GLOBAL RULE: No Hardcoded AI Responses
**CRITICAL:** All AI-generated content must be dynamic and NOT hardcoded. When using AI APIs:
- Always call the AI API with appropriate system prompts
- Never hardcode response text, suggestions, impacts, or explanations
- Use AI to generate contextual, personalized responses
- Only hardcode fallback error messages when AI is unavailable
- System prompts should be well-designed to get the desired output format

**Examples of what to avoid:**
- ❌ Hardcoded: "Severe anemia - may cause extreme fatigue"
- ✅ AI-generated: Call OpenAI with system prompt to generate impact based on parameter value

**When AI is unavailable:**
- Provide generic fallback: "Unable to analyze - please consult doctor"
- Never make up specific medical advice without AI

---

## PHASE 1: Database Schema Enhancement (Local SQLite)
**Goal:** Expand database to support doctors, prescriptions, and enhanced patient records.

### Phase 1.1: Add Doctors Table
- Create `doctors` table with fields:
  - id (TEXT PRIMARY KEY)
  - name (TEXT)
  - specialty (TEXT) - Cardiology, General Medicine, Pediatrics, etc.
  - phone (TEXT)
  - is_active (BOOLEAN)
- Seed 5-10 proxy doctors:
  - Dr. Anus Kumar (Cardiology)
  - Dr. Priya Sharma (General Medicine)
  - Dr. Rajesh Gupta (Pediatrics)
  - Dr. Meena Patel (Orthopedics)
  - Dr. Vikram Singh (Dermatology)
  - Dr. Sunita Verma (Gynecology)
  - Dr. Amit Kumar (Neurology)
  - Dr. Kavita Rao (Ophthalmology)

### Phase 1.2: Add Prescriptions Table
- Create `prescriptions` table with fields:
  - id (INTEGER PRIMARY KEY AUTOINCREMENT)
  - patient_id (TEXT)
  - visit_id (INTEGER) - Link to visits table
  - doctor_id (TEXT)
  - doctor_notes (TEXT)
  - medications (JSON) - Array of {name, type, dosage, quantity, frequency}
  - created_at (TEXT)
  - language (TEXT) - Patient's preferred language

### Phase 1.3: Enhance Queue Table
- Add `assigned_doctor_id` field to queue table
- Add `consultation_type` field (initial, follow-up, emergency)

### Phase 1.4: Add Report Comparison Table
- Create `report_comparisons` table with fields:
  - id (INTEGER PRIMARY KEY AUTOINCREMENT)
  - patient_id (TEXT)
  - past_report_id (INTEGER)
  - present_report_id (INTEGER)
  - comparison_summary (JSON) - Improvements, deteriorations, unchanged
  - created_at (TEXT)

### Phase 1.5: Update Backend API Endpoints
- Add CRUD endpoints for doctors
- Add endpoints for prescriptions
- Update queue endpoint to assign doctor automatically
- Add report comparison endpoint

---

## PHASE 2: Report Analyzer - Color-Coded Parameters
**Goal:** Implement visual highlighting of abnormal parameters in report summaries.

### Phase 2.1: Backend - Parameter Analysis Enhancement
- Create function `analyze_parameter_normality(parameter_name, value)`:
  - Define normal ranges for common parameters:
    - Hemoglobin: 12-17 g/dL (male), 11-15 g/dL (female)
    - Blood Pressure: 90-120 / 60-80 mmHg
    - Blood Sugar: 70-140 mg/dL (fasting), <180 mg/dL (post-meal)
    - WBC Count: 4,500-11,000 cells/μL
    - Platelets: 150,000-450,000/μL
    - Cholesterol: <200 mg/dL
  - Return status: 'normal', 'slightly_abnormal', 'severely_abnormal'

### Phase 2.2: Backend - Enhanced Report Analysis
- Modify `analyze_report_for_key_points()` to return structured data:
  ```json
  {
    "key_points": ["Hemoglobin: 9.8 g/dL"],
    "parameters": [
      {
        "name": "Hemoglobin",
        "value": "9.8 g/dL",
        "unit": "g/dL",
        "status": "severely_low",
        "normal_range": "12-17 g/dL",
        "impact": "May cause fatigue, weakness"
      }
    ]
  }
  ```

### Phase 2.3: Frontend - Color-Coded Display Component
- Create `ParameterCard` component in `components/ui/parameter-card.tsx`:
  - Props: name, value, status, normal_range, impact
  - Styling:
    - Red text/border for severely_abnormal
    - Yellow text/border for slightly_abnormal
    - Green/normal for normal
  - Display impact/suggestion in patient's language

### Phase 2.4: Frontend - Update Summary Page
- Integrate `ParameterCard` into existing Summary component
- Map report key points to parameter cards
- Apply color coding based on status

---

## PHASE 3: Report Analyzer - Language Translation
**Goal:** Ensure report summaries are in patient's selected language.

### Phase 3.1: Backend - Translation Service
- Create function `translate_medical_summary(text, target_language)`:
  - Use OpenAI GPT-4o-mini for translation
  - Preserve medical terminology accuracy
  - Include cultural context for explanations

### Phase 3.2: Backend - Update Summary Endpoint
- Modify `/summary` endpoint to:
  - Keep clinical summary in English (for doctors)
  - Add `patient_summary` field translated to patient's language
  - Translate parameter impacts and suggestions

### Phase 3.3: Frontend - Display Translated Summary
- Show translated summary to patient in Dashboard
- Keep English version for doctor portal

---

## PHASE 4: Report Analyzer - Compare Two Reports
**Goal:** Enable patients to compare past and present reports.

### Phase 4.1: Backend - Report Comparison Logic
- Create function `compare_reports(past_report, present_report)`:
  - Extract parameters from both reports
  - Compare values
  - Identify:
    - Improved parameters
    - Deteriorated parameters
    - New abnormalities
    - Resolved abnormalities
  - Generate comparison summary

### Phase 4.2: Backend - Comparison Endpoint
- Add `POST /patients/{patient_id}/reports/compare`:
  - Accept: past_report_id, present_report_id
  - Return: comparison summary with status indicators

### Phase 4.3: Frontend - Report Comparison UI
- Create `ReportComparison` component:
  - Two report selection dropdowns
  - Side-by-side parameter comparison
  - Visual indicators (↑ improved, ↓ deteriorated, → unchanged)
  - Summary in patient's language

### Phase 4.4: Frontend - Integrate into Dashboard
- Add "Compare Reports" button in Lab Reports section
- Show comparison results modal

---

## PHASE 5: Patient Dashboard Enhancement
**Goal:** Build comprehensive patient dashboard with sidebar navigation.

### Phase 5.1: Backend - Enhanced Patient Data Endpoint
- Update `GET /patients/{patient_id}` to return:
  - Basic info
  - Latest visit summary
  - Assigned doctor
  - Recent prescriptions
  - All reports

### Phase 5.2: Frontend - Dashboard Layout Structure
- Create `app/[locale]/dashboard/page.tsx`:
  - Hero section: Patient name, ID, last visit date, assigned doctor
  - Sidebar navigation:
    - Overview
    - Patient Records
    - Lab Reports
    - Prescriptions
    - Visit History

### Phase 5.3: Frontend - Patient Records Section
- Display patient profile details
- Edit functionality (phone, address)
- Medical history timeline

### Phase 5.4: Frontend - Lab Reports Section with Report Analyzer
- List all uploaded reports
- **View Report button (opens Report Analyzer)**:
  - Display report with color-coded parameters (red/yellow/green)
  - Show parameter status (normal, slightly abnormal, severely abnormal)
  - Display impact/suggestions in patient's language
  - Show extracted key points
- Download report button
- Delete report button
- **Compare Reports button**:
  - Select two reports (past and present)
  - Show side-by-side comparison
  - Display improvement/deterioration indicators (↑ ↓ →)
  - Show comparison summary in patient's language

### Phase 5.5: Frontend - Prescriptions Section
- List all prescriptions from visits
- View prescription details
- Download prescription as PDF
- Print prescription

### Phase 5.6: Frontend - Visit History Section
- Timeline of all visits
- Each visit shows:
  - Date
  - Doctor
  - Chief complaint
  - Summary

---

## PHASE 6: Doctor Authentication
**Goal:** Implement doctor login system.

### Phase 6.1: Backend - Doctor Login Endpoint
- Add `POST /doctors/login`:
  - Accept: doctor_id (or phone)
  - Return: doctor details, authentication token (simple JWT or session)

### Phase 6.2: Frontend - Doctor Login Page
- Create `app/[locale]/doctor-login/page.tsx`:
  - Input: Doctor ID
  - Simple authentication
  - Redirect to doctor dashboard on success

### Phase 6.3: Frontend - Auth State Management
- Add doctor session state
- Store in localStorage for simplicity
- Add logout functionality

---

## PHASE 7: Doctor Dashboard
**Goal:** Build doctor portal with patient management.

### Phase 7.1: Backend - Doctor's Patients Endpoint
- Add `GET /doctors/{doctor_id}/patients`:
  - Return all patients assigned to this doctor
  - Include queue status, visit history

### Phase 7.2: Frontend - Doctor Dashboard Layout
- Create `app/[locale]/doctor-dashboard/page.tsx`:
  - Header: Doctor name, specialty
  - Patient list table:
    - Patient name
    - Token number
    - Priority
    - Status (waiting, in consultation, completed)
    - Action: "Review Patient"

### Phase 7.3: Frontend - Patient Queue Management
- Display real-time queue for assigned patients
- Filter by status
- Sort by priority

---

## PHASE 8: Doctor - Review Patient Page
**Goal:** Create detailed patient review interface for doctors.

### Phase 8.1: Backend - Patient Review Data Endpoint
- Add `GET /doctors/{doctor_id}/patients/{patient_id}/review`:
  - Return complete patient data:
    - Profile
    - Vitals
    - Reports with analysis
    - Visit history
    - Previous prescriptions
    - Conversation summary

### Phase 8.2: Frontend - Review Patient Page
- Create `app/[locale]/doctor-dashboard/review/[patient_id]/page.tsx`:
  - Patient info header
  - Sections:
    - Vitals (color-coded)
    - Reports (with key points)
    - Visit history
    - Previous prescriptions

### Phase 8.3: Frontend - Doctor Notes Section
- Text area for doctor notes
- Voice input option (use existing speech-to-text)
- Auto-save to database

### Phase 8.4: Frontend - Prescription Builder
- Create `PrescriptionBuilder` component:
  - Add medication form:
    - Name (autocomplete/dropdown)
    - Type (tablet, syrup, injection, etc.)
    - Dosage
    - Quantity
    - Frequency (once daily, twice daily, etc.)
    - Duration
  - Medication list with remove option
  - Save prescription button

---

## PHASE 9: Handwritten Report to Digital
**Goal:** Enable doctors to upload handwritten prescriptions/reports.

### Phase 9.1: Backend - Handwriting OCR
- Add `POST /doctors/upload-handwritten`:
  - Accept image file
  - Use OpenAI GPT-4o Vision for OCR
  - Extract text and structure
  - Return structured data

### Phase 9.2: Frontend - Handwritten Upload UI
- Add upload button in review page
- Preview uploaded image
- Show extracted text for verification
- Edit extracted text before saving

---

## PHASE 10: Language Conversion for Reports
**Goal:** Generate patient reports in their selected language.

### Phase 10.1: Backend - Report Generation Endpoint
- Add `POST /doctors/{doctor_id}/patients/{patient_id}/generate-report`:
  - Accept: doctor_notes, prescription, language
  - Generate comprehensive report:
    - Patient info
    - Doctor notes
    - Prescription
    - Summary
  - Translate to patient's language

### Phase 10.2: Frontend - Generate & Display Report
- Add "Generate Report" button in review page
- Show preview of generated report
- Download PDF option
- Print option

---

## PHASE 11: Token to Doctor Assignment
**Goal:** Automatically assign doctor when generating token.

### Phase 11.1: Backend - Doctor Assignment Logic
- Modify `POST /queue` to:
  - Analyze patient symptoms/priority
  - Match with appropriate doctor specialty
  - Assign doctor to queue entry
  - Return assigned doctor info

### Phase 11.2: Backend - Specialty Matching
- Create specialty mapping:
  - Chest pain/breathlessness → Cardiology
  - Children → Pediatrics
  - Bone/joint issues → Orthopedics
  - Skin issues → Dermatology
  - Eye issues → Ophthalmology
  - Neurological symptoms → Neurology
  - Women's health → Gynecology
  - Default → General Medicine

### Phase 11.3: Frontend - Display Assigned Doctor
- Show assigned doctor on token page
- Show on patient dashboard

---

## PHASE 12: Print Dashboard
**Goal:** Enable printing of patient dashboard.

### Phase 12.1: Frontend - Print Styles
- Add CSS print media queries
- Hide sidebar, buttons
- Format for A4 paper
- Include all relevant sections

### Phase 12.2: Frontend - Print Button
- Add print button in patient dashboard
- Print doctor review page
- Print generated report

---

## PHASE 13: Doctor Reassignment
**Goal:** Allow changing assigned doctor.

### Phase 13.1: Backend - Reassign Doctor Endpoint
- Add `PATCH /queue/{queue_id}/reassign`:
  - Accept: new_doctor_id
  - Update queue entry
  - Notify system

### Phase 13.2: Frontend - Reassign UI
- Add "Change Doctor" option in review page
- Doctor selection dropdown
- Confirmation dialog

---

## PHASE 14: Testing & Validation
**Goal:** Comprehensive testing of all features.

### Phase 14.1: Database Testing
- Verify all tables created correctly
- Test CRUD operations
- Test foreign key relationships
- Test data persistence

### Phase 14.2: API Testing
- Test all new endpoints
- Test error handling
- Test authentication
- Test file uploads

### Phase 14.3: Frontend Testing
- Test patient registration flow
- Test doctor login
- Test dashboard navigation
- Test report upload and analysis
- Test prescription creation
- Test report generation
- Test language switching
- Test print functionality

### Phase 14.4: Integration Testing
- End-to-end patient flow
- End-to-end doctor flow
- Report comparison flow
- Multi-language testing

---

## PHASE 15: Documentation & Cleanup
**Goal:** Finalize documentation and code cleanup.

### Phase 15.1: Update README
- Document new features
- Update API endpoints list
- Add setup instructions for new features

### Phase 15.2: Code Review
- Remove unused code
- Optimize database queries
- Add error handling
- Add input validation

### Phase 15.3: User Guide
- Create user guide for patients
- Create user guide for doctors
- Add screenshots where applicable

---

## Implementation Notes

### Database Persistence
- Currently using in-memory SQLite (resets on restart)
- For production, change to file-based SQLite:
  - Update `DB_PATH = ':memory:'` to `DB_PATH = 'synapse.db'`
  - Add backup mechanism

### AI API Usage
- All features use OpenAI GPT-4o-mini (cost-effective)
- Implement rate limiting if needed
- Add fallback for API failures

### File Storage
- Currently storing reports in database as base64
- Consider moving to file system for large files
- Add file cleanup for old reports

### Security Considerations
- Add proper authentication (JWT or sessions)
- Add input sanitization
- Add file upload validation
- Add rate limiting

---

## Phase Dependencies

```
Phase 1 (Database) MUST be completed first
Phase 2, 3, 4 (Report Analyzer) can run in parallel after Phase 1
Phase 5 (Patient Dashboard) depends on Phase 1
Phase 6 (Doctor Auth) depends on Phase 1
Phase 7 (Doctor Dashboard) depends on Phase 6
Phase 8 (Review Page) depends on Phase 7
Phase 9 (Handwriting) depends on Phase 8
Phase 10 (Report Gen) depends on Phase 8
Phase 11 (Doctor Assignment) depends on Phase 1
Phase 12 (Print) depends on Phase 5, 8
Phase 13 (Reassign) depends on Phase 8
Phase 14 (Testing) depends on all previous
Phase 15 (Docs) depends on all previous
```

---

## Estimated Complexity per Phase

- Phase 1: Medium (Database schema design)
- Phase 2: Medium (Analysis logic)
- Phase 3: Low (Translation wrapper)
- Phase 4: Medium (Comparison algorithm)
- Phase 5: High (UI heavy)
- Phase 6: Low (Simple auth)
- Phase 7: Medium (Dashboard UI)
- Phase 8: High (Complex UI)
- Phase 9: Medium (OCR integration)
- Phase 10: Medium (Report generation)
- Phase 11: Low (Assignment logic)
- Phase 12: Low (Print styles)
- Phase 13: Low (Simple update)
- Phase 14: High (Comprehensive testing)
- Phase 15: Low (Documentation)

---

## Success Criteria

✅ Database supports all new features
✅ Report parameters are color-coded correctly
✅ Report summaries work in all supported languages
✅ Report comparison shows accurate improvements/deteriorations
✅ Patient dashboard is fully functional with all sections
✅ Doctor login works correctly
✅ Doctor dashboard shows assigned patients
✅ Doctor can review patients with all details
✅ Doctor can create prescriptions
✅ Handwritten reports convert to digital text
✅ Reports generate in patient's language
✅ Token assigns appropriate doctor
✅ Print functionality works
✅ Doctor reassignment works
✅ All features tested and error-free
✅ Documentation complete

---

**Status: Phase 15 Completed ✅ (All phases complete)**

## Completion Summary

All 15 phases have been successfully completed:

✅ **Phase 1**: Database Schema Enhancement - Added doctors, prescriptions, report_comparisons tables
✅ **Phase 2**: Report Analyzer - Color-Coded Parameters - AI-powered parameter analysis with color coding
✅ **Phase 3**: Report Analyzer - Language Translation - Multi-language support for summaries
✅ **Phase 4**: Report Analyzer - Compare Two Reports - AI-powered report comparison
✅ **Phase 5**: Patient Dashboard Enhancement - Comprehensive patient dashboard
✅ **Phase 6**: Doctor Authentication - Doctor login system
✅ **Phase 7**: Doctor Dashboard - Patient management interface
✅ **Phase 8**: Doctor - Review Patient Page - Detailed patient review with prescription builder
✅ **Phase 9**: Handwritten Report to Digital - OCR for handwritten prescriptions
✅ **Phase 10**: Language Conversion for Reports - Report generation in patient's language
✅ **Phase 11**: Token to Doctor Assignment - Automatic specialty-based doctor assignment
✅ **Phase 12**: Print Dashboard - Print functionality for dashboards and reports
✅ **Phase 13**: Doctor Reassignment - Ability to change assigned doctor
✅ **Phase 14**: Testing & Validation - Comprehensive testing completed
✅ **Phase 15**: Documentation & Cleanup - Documentation completed

## Deliverables

- ✅ Enhanced backend with all features (main.py)
- ✅ Frontend with patient and doctor portals
- ✅ Database schema with all required tables
- ✅ API endpoints for all features
- ✅ Updated README.md with complete documentation
- ✅ PATIENT_GUIDE.md - User guide for patients
- ✅ DOCTOR_GUIDE.md - User guide for doctors
- ✅ All AI features implemented with no hardcoded medical advice
- ✅ Multi-language support for 23 Indian languages
- ✅ Color-coded parameter analysis
- ✅ Report comparison functionality
- ✅ Handwritten OCR capability
- ✅ Print functionality

## Project Status: COMPLETE 🎉
