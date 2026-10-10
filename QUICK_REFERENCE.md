# Synapse AI - Doctor Dashboard Quick Reference

**For the developer implementing the doctor dashboard (Person 3)**

---

## 🚀 Quick Start

### 1. What You're Building
Doctor dashboard where doctors can:
- View queue of waiting patients
- Consult patients (view intake data, add notes, write prescriptions)
- Upload prescription images with OCR extraction
- Generate PDF analytics reports
- Complete consultations

### 2. What Already Exists
- **Patient intake system** (Person 1) - COMPLETED
  - Frontend: `app/page.tsx` (all patient flow)
  - Backend: `backend/main.py` (FastAPI with SQLite)
  - Database: patients, visits, reports, queue tables
- **Authentication system** (Person 2) - IN PROGRESS
  - Will integrate later, use simple login for now

### 3. Your Starting Point
- Clone repository
- Run `pnpm install` (frontend)
- Run `cd backend && py -m pip install -r requirements.txt` (backend)
- Start backend: `cd backend && py main.py` (runs on :8000)
- Start frontend: `pnpm dev` (runs on :3000)

---

## 📁 Key Files to Know

### Frontend
```
app/page.tsx              # Patient intake (all modes in one file)
app/globals.css           # Design system & styles
app/layout.tsx            # Root layout
components/ui/button.tsx  # Button component
lib/utils.ts              # cn() utility
```

### Backend
```
backend/main.py           # FastAPI application
backend/requirements.txt  # Python dependencies
```

### Design System
```css
Colors:
- Background: #f5f1e8 (cream)
- Borders: #141414 (black)
- Accent: #e44f2b (coral/red)
- Mint: #b9dbcb
- Yellow: #f5cf4a
- Green: #236b52

Classes:
- .display  (page headings)
- .eyebrow  (section labels)
- .panel    (section containers)
- .action   (primary buttons)
- .button-primary
- .button-secondary
- .metric   (stat displays)
- .label    (field labels)
```

---

## 🗄️ Database Schema

### Existing Tables (Person 1)
```sql
patients      -- id, name, age, phone, sex, vitals, created_at
reports       -- id, patient_id, filename, content_type, bytes, created_at
visits        -- id, patient_id, visit_date, summary, symptoms, risk, priority, created_at
queue         -- id, patient_id, token, priority, status, created_at
```

### New Tables (You Add)
```sql
doctors       -- id, name, specialty, available, created_at
prescriptions -- id, patient_id, visit_id, doctor_id, medications, notes, diagnosis, created_at
doctor_notes  -- id, patient_id, visit_id, doctor_id, content, created_at
```

---

## 🔌 API Endpoints

### Existing (Person 1)
```
GET  /health
POST /patients
GET  /patients/{patient_id}
POST /patients/{patient_id}/reports
GET  /patients/{patient_id}/reports
DELETE /patients/{patient_id}/reports/{report_id}
POST /conversation/next
POST /summary
GET  /queue
POST /queue
PATCH /queue/{queue_id}/status
GET  /patients/{patient_id}/visits
```

### New (You Add)
```
POST /doctors/login
GET  /doctors/{doctor_id}
GET  /doctors
GET  /queue/doctor?doctor_id={doctor_id}
POST /queue/{queue_id}/assign
GET  /consultation/{patient_id}
POST /consultation/{patient_id}/notes
GET  /consultation/{patient_id}/notes
POST /consultation/{patient_id}/prescription
POST /consultation/{patient_id}/prescription/upload
GET  /consultation/{patient_id}/prescriptions
GET  /consultation/{patient_id}/pdf
POST /consultation/{patient_id}/complete
```

---

## 📦 New Dependencies

### Add to `backend/requirements.txt`
```
reportlab          # PDF generation
pytesseract        # OCR
Pillow             # Image processing
```

### System Dependencies
```
Tesseract OCR (install separately)
- Windows: Download from GitHub
- Mac: brew install tesseract
- Linux: sudo apt-get install tesseract-ocr
```

---

## 🎯 Implementation Order

### Phase 1: Backend (Week 1)
1. Add database tables to `main.py`
2. Add Pydantic models
3. Implement authentication endpoints (simple for now)
4. Implement queue/doctor endpoints
5. Implement consultation endpoints
6. Implement PDF generation (ReportLab)
7. Implement OCR (Tesseract)
8. Test all endpoints

### Phase 2: Frontend (Week 2)
1. Create `app/doctor/page.tsx` (queue view)
2. Create `app/doctor/consultation/[patient_id]/page.tsx`
3. Implement QueueList component
4. Implement ConsultationView component
5. Implement DoctorNotes component
6. Implement PrescriptionForm component
7. Implement PrescriptionUpload component
8. Implement PDFGenerator component
9. Test complete flow

### Phase 3: Integration (Week 3)
1. Connect with patient intake (test with real data)
2. Add real-time queue updates (polling)
3. Error handling
4. Responsive design
5. Final testing

---

## 🔧 Key Code Patterns

### Backend - Add Table
```python
c.execute('CREATE TABLE IF NOT EXISTS doctors (id TEXT PRIMARY KEY,name TEXT,specialty TEXT,available BOOLEAN,created_at TEXT)')
c.commit()
```

### Backend - Add Endpoint
```python
@app.post('/doctors/login')
def doctor_login(doctor: DoctorLogin):
    # Validate credentials
    # Return doctor_id and token
    pass
```

### Frontend - API Call
```typescript
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const response = await fetch(`${API}/consultation/${patientId}`, {
  method: 'GET',
  headers: { 'Content-Type': 'application/json' }
})
const data = await response.json()
```

### Frontend - Component Structure
```typescript
export default function DoctorDashboard() {
  const [queue, setQueue] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchQueue()
  }, [])

  return (
    <main className="min-h-screen bg-[#f5f1e8]">
      <Header />
      <QueueList queue={queue} />
    </main>
  )
}
```

---

## 🎨 Design System Examples

### Panel Component
```tsx
<div className="panel border-2 border-[#141414] bg-white p-7 shadow-[8px_8px_0_#141414]">
  <p className="eyebrow">Section Label</p>
  <h2 className="display text-3xl font-black">Heading</h2>
</div>
```

### Priority Badge
```tsx
<span className={`px-3 py-1 text-xs font-black uppercase ${
  priority === 'high' ? 'bg-[#e44f2b] text-white' :
  priority === 'medium' ? 'bg-[#f5cf4a]' :
  'bg-[#236b52] text-white'
}`}>
  {priority} priority
</span>
```

### Button
```tsx
<button className="action border-2 border-[#141414] bg-[#e44f2b] text-white px-4 py-3 font-black">
  Action Button
</button>
```

---

## 📊 Data Flow

```
Patient Intake (Person 1)
  ↓
Patient added to queue
  ↓
Doctor Dashboard (You)
  ↓
View queue → Select patient
  ↓
View consultation data
  ↓
Add notes → Write prescription → Upload image (OCR) → Generate PDF
  ↓
Complete consultation
  ↓
Patient dashboard shows prescription
```

---

## ✅ Success Checklist

Backend:
- [ ] All new tables created
- [ ] All new endpoints implemented
- [ ] OCR extraction works
- [ ] PDF generation works
- [ ] Error handling in place

Frontend:
- [ ] Queue view displays patients
- [ ] Consultation view loads data
- [ ] Notes can be added
- [ ] Prescription can be written
- [ ] Image upload works
- [ ] OCR populates fields
- [ ] PDF generates and downloads
- [ ] Consultation can be completed

Integration:
- [ ] Works with patient intake data
- [ ] Queue updates in real-time
- [ ] Patient sees prescriptions
- [ ] Design system consistent
- [ ] No critical bugs

---

## 🚨 Important Notes

### Security
- Never expose API keys in frontend
- Validate all inputs on backend
- Sanitize OCR-extracted text
- Use HTTPS in production

### Medical
- This is a prototype, not production software
- Clinical decisions with qualified professionals only
- AI recommendations are for reference only
- OCR may have errors - always review manually

### Coordination
- Share database schema changes with team
- Document any API contract changes
- Coordinate with Person 2 for auth integration
- Test integration when all features complete

---

## 📚 Documentation

- Full plan: `DOCTOR_DASHBOARD_PLAN.md`
- Architecture: `ARCHITECTURE_DIAGRAM.md`
- Existing system: `report.md`
- README: `README.md`

---

## 🆘 Troubleshooting

### Backend won't start
- Check Python version (3.14+)
- Install dependencies: `py -m pip install -r requirements.txt`
- Check port 8000 is not in use

### OCR not working
- Install Tesseract OCR system-wide
- Add Tesseract to PATH
- Test with: `py -c "import pytesseract; print(pytesseract.get_tesseract_version())"`

### PDF generation fails
- Install ReportLab: `py -m pip install reportlab`
- Check for import errors

### Frontend won't build
- Run `pnpm install`
- Check Node.js version (18+)
- Clear .next cache: `rm -rf .next`

---

## 📞 Contact

- Person 1 (Patient Intake): COMPLETED
- Person 2 (Authentication): IN PROGRESS
- Person 3 (Doctor Dashboard): YOU
- Integration: Final phase

---

**Good luck! You're building the doctor consultation interface that will help healthcare professionals provide better care.** 🏥✨
