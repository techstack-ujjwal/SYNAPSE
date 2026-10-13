# Doctor User Guide - Synapse AI

Welcome to Synapse AI Doctor Portal. This guide will help you navigate the doctor dashboard and manage your patients effectively.

## Getting Started

### Step 1: Login
1. Visit the doctor login page
2. Enter your Doctor ID (e.g., DOC-001)
3. Click "Login"
4. You'll be redirected to your dashboard

**Note**: Your Doctor ID is provided by the hospital administration.

### Step 2: View Your Dashboard
The doctor dashboard shows:
- Your name and specialty
- List of assigned patients
- Patient queue status (waiting, in consultation, completed)
- Token numbers and priority levels
- Estimated wait times

## Managing Patients

### View Patient List
1. On your dashboard, you'll see all assigned patients
2. Each patient shows:
   - Name and age
   - Token number
   - Priority level (low/medium/high)
   - Status (waiting/in consultation/completed)
3. Click "Review Patient" to see full details

### Review Patient Details
When you click "Review Patient", you'll see:
- **Patient Profile**: Name, age, sex, phone, vitals
- **Reports**: All uploaded medical reports with AI analysis
- **Visit History**: Previous consultations and summaries
- **Prescriptions**: Current and past medications
- **Conversation Summary**: AI-generated summary of patient's symptoms

### Understanding Report Analysis
Each report shows:
- **Key Points**: AI-extracted clinical findings in English
- **Parameters**: Color-coded analysis
  - 🟢 Green: Normal values
  - 🟡 Yellow: Slightly abnormal
  - 🔴 Red: Severely abnormal
- **Impact**: AI-generated explanation of what this means
- **Suggestions**: AI-generated recommendations

## Creating Prescriptions

### Step 1: Access Prescription Builder
1. Open patient review page
2. Scroll to "Prescription" section
3. Click "Add Medication"

### Step 2: Add Medications
For each medication, provide:
- **Name**: Medication name (autocomplete available)
- **Type**: Tablet, syrup, injection, etc.
- **Dosage**: e.g., 500mg, 5ml
- **Quantity**: Number of units
- **Frequency**: Once daily, twice daily, etc.
- **Duration**: e.g., 7 days, 2 weeks

### Step 3: Save Prescription
1. Review the medication list
2. Add doctor notes (optional)
3. Click "Save Prescription"
4. Prescription saved to patient's record

## Handwritten Prescriptions

### Upload Handwritten Report
1. In patient review page, click "Upload Handwritten"
2. Select image file (JPG, PNG, WebP)
3. AI will extract text using OCR
4. Review extracted text for accuracy
5. Edit if needed
6. Save to patient record

**Supported formats**:
- Handwritten prescriptions
- Doctor's notes
- Medical reports
- Lab results

## Generating Patient Reports

### Step 1: Generate Report
1. In patient review page, click "Generate Report"
2. Provide:
   - Doctor notes
   - Diagnosis
   - Medications (auto-filled from prescription)
3. Select patient's language
4. Click "Generate"

### Step 2: Review and Download
1. AI generates report in patient's language
2. Review the generated content
3. Download as PDF
4. Print if needed

**Report includes**:
- Patient information
- Doctor information
- Consultation details
- Diagnosis
- Prescription/medications
- Doctor's notes
- Follow-up instructions

## Doctor Reassignment

### When to Reassign
- If specialty doesn't match patient's condition
- If doctor is unavailable
- If patient requests different doctor

### How to Reassign
1. In patient review page, click "Change Doctor"
2. Select new doctor from dropdown
3. Confirm the change
4. Patient reassigned automatically

## Queue Management

### Monitor Queue
- See real-time queue status
- Filter by status (waiting/in consultation/completed)
- Sort by priority

### Update Patient Status
- Change patient status from waiting to in consultation
- Mark consultation as completed
- Status updates automatically reflect in queue

## Print Functionality

### Print Patient Dashboard
1. Click "Print" button on patient dashboard
2. Prints all relevant sections
- Patient profile
- Vitals
- Reports
- Visit history
- Prescriptions

### Print Generated Report
1. After generating report, click "Print"
2. Prints in A4 format
- Clean layout
- All sections included
- Ready for signature

## AI Features Explained

### Report Analysis
- AI extracts key clinical findings
- Color-coded parameter analysis
- Normal range comparisons
- Impact and suggestions generated per patient

### Patient Summaries
- AI summarizes patient conversations
- Extracts symptoms automatically
- Identifies red flags
- Provides risk assessment

### Translation
- Reports generated in patient's language
- Medical terminology preserved
- Culturally appropriate translations
- Multiple languages supported

## Best Practices

### Before Consultation
1. Review patient's AI-generated summary
2. Check uploaded reports with analysis
3. Review previous visit history
4. Note any red flags from AI

### During Consultation
1. Use AI analysis as reference, not replacement
2. Verify AI findings with clinical judgment
3. Update doctor notes in real-time
4. Create prescriptions as needed

### After Consultation
1. Generate patient report in their language
2. Ensure prescriptions are clear
3. Provide follow-up instructions
4. Mark consultation as completed

### For Handwritten Notes
1. Upload handwritten prescriptions for OCR
2. Review extracted text carefully
3. Edit any errors
4. Save accurate records

## Troubleshooting

### Can't Login
- Verify Doctor ID is correct
- Check if you're marked as active
- Contact hospital administration

### Patient Not Showing in Queue
- Patient may not have joined queue yet
- Check if patient assigned to different doctor
- Verify patient registration

### Report Analysis Failed
- Check if report is readable
- Ensure file format is supported
- Try uploading again
- Contact support if issue persists

### Prescription Not Saving
- Check all required fields are filled
- Verify medication name is valid
- Try again after a few seconds

### Can't Generate Report
- Ensure doctor notes are provided
- Check if medications are selected
- Verify patient language is set
- Try again or contact support

## Data Privacy

- Only access patients assigned to you
- Patient data is encrypted
- Conversations are stored securely
- Follow hospital privacy policies
- Log out after use

## Keyboard Shortcuts

(If available in your implementation)
- `Ctrl+P`: Print current page
- `Ctrl+S`: Save current work
- `Esc`: Close modal/dialog

## Support

For technical issues:
- Contact hospital IT support
- Check system status page
- Report bugs through hospital channels

For clinical questions:
- Consult with senior doctors
- Refer to medical guidelines
- Use clinical judgment

---

**Note**: This is a prototype system. Always use clinical judgment alongside AI insights. AI is a tool to assist, not replace, medical expertise.
