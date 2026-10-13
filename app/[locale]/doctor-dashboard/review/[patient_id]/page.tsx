'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ArrowLeft, Save, Plus, X, FileText, Activity, AlertCircle, CheckCircle2, Upload, Download, FileImage, Sparkles, Printer, RefreshCw } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ReviewPatientPage() {
  const router = useRouter()
  const params = useParams()
  const [doctor, setDoctor] = useState<any>(null)
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [notes, setNotes] = useState('')
  const [medications, setMedications] = useState<any[]>([])
  const [newMed, setNewMed] = useState({ name: '', type: 'tablet', dosage: '', quantity: '', frequency: 'once daily' })
  const [handwrittenFile, setHandwrittenFile] = useState<File | null>(null)
  const [handwrittenPreview, setHandwrittenPreview] = useState<string>('')
  const [extractedText, setExtractedText] = useState('')
  const [extracting, setExtracting] = useState(false)
  const [diagnosis, setDiagnosis] = useState('')
  const [generatedReport, setGeneratedReport] = useState('')
  const [generatingReport, setGeneratingReport] = useState(false)
  const [showReassignModal, setShowReassignModal] = useState(false)
  const [allDoctors, setAllDoctors] = useState<any[]>([])
  const [selectedDoctor, setSelectedDoctor] = useState('')

  useEffect(() => {
    const doc = localStorage.getItem('doctor')
    if (!doc) return router.push(`/${params.locale}/doctor-login`)
    const docData = JSON.parse(doc)
    setDoctor(docData)
    fetch(`${API}/doctors/${docData.id}/patients/${params.patient_id}/review`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false))

    // Fetch all doctors for reassignment
    fetch(`${API}/doctors`)
      .then(r => r.json())
      .then(setAllDoctors)
      .catch(() => {})
  }, [router, params.locale, params.patient_id])

  const addMedication = () => {
    if (!newMed.name || !newMed.dosage) return
    setMedications([...medications, { ...newMed, id: Date.now() }])
    setNewMed({ name: '', type: 'tablet', dosage: '', quantity: '', frequency: 'once daily' })
  }

  const removeMedication = (id: number) => setMedications(m => m.filter(x => x.id !== id))

  const handleHandwrittenUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setHandwrittenFile(file)
    setExtracting(true)

    // Create preview
    const reader = new FileReader()
    reader.onloadend = () => {
      setHandwrittenPreview(reader.result as string)
    }
    reader.readAsDataURL(file)

    // Upload for OCR
    const formData = new FormData()
    formData.append('report', file)
    formData.append('patient_id', params.patient_id as string)
    formData.append('language', 'English')

    try {
      const response = await fetch(`${API}/doctors/upload-handwritten?patient_id=${params.patient_id}&language=English`, {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      if (result.ok) {
        setExtractedText(result.extracted_text || '')
        // Auto-fill medications if structured data available
        if (result.structured_data?.medications) {
          const meds = result.structured_data.medications.map((m: any, i: number) => ({
            ...m,
            id: Date.now() + i,
            type: m.type || 'tablet',
            dosage: m.dosage || '',
            quantity: m.quantity || '',
            frequency: m.frequency || 'once daily'
          }))
          setMedications([...medications, ...meds])
        }
        if (result.structured_data?.diagnosis) {
          setDiagnosis(result.structured_data.diagnosis)
        }
      }
    } catch (error) {
      alert('Failed to extract text from image')
    } finally {
      setExtracting(false)
    }
  }

  const generatePatientReport = async () => {
    if (!doctor || !data) return
    setGeneratingReport(true)

    try {
      const response = await fetch(`${API}/doctors/${doctor.id}/patients/${params.patient_id}/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: params.patient_id,
          doctor_id: doctor.id,
          doctor_notes: notes,
          medications,
          diagnosis,
          language: 'English'
        })
      })
      const result = await response.json()
      if (result.report_content) {
        setGeneratedReport(result.report_content)
      }
    } catch (error) {
      alert('Failed to generate report')
    } finally {
      setGeneratingReport(false)
    }
  }

  const downloadReport = () => {
    if (!generatedReport) return
    const blob = new Blob([generatedReport], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${data?.patient?.name}_${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleReassignDoctor = async () => {
    if (!selectedDoctor) return

    try {
      const response = await fetch(`${API}/queue/reassign-by-patient`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: params.patient_id,
          new_doctor_id: selectedDoctor
        })
      })

      if (response.ok) {
        alert('Doctor reassigned successfully')
        setShowReassignModal(false)
        setSelectedDoctor('')
        // Refresh data
        fetch(`${API}/doctors/${doctor.id}/patients/${params.patient_id}/review`)
          .then(r => r.json())
          .then(setData)
      } else {
        alert('Failed to reassign doctor')
      }
    } catch (error) {
      alert('Error reassigning doctor')
    }
  }

  const savePrescription = () => {
    if (!doctor || !data) return
    fetch(`${API}/prescriptions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: params.patient_id,
        doctor_id: doctor.id,
        doctor_notes: notes,
        medications,
        language: 'English'
      })
    }).then(() => alert('Prescription saved')).catch(() => alert('Failed to save'))
  }

  if (loading) return <div className="min-h-screen bg-[#f5f1e8] flex items-center justify-center"><Activity className="size-8 animate-spin text-[#e44f2b]" /></div>

  return (
    <main className="min-h-screen bg-[#f5f1e8]">
      <header className="flex items-center justify-between px-5 py-5 lg:px-10 border-b-2 border-[#141414] bg-white">
        <button onClick={() => router.push(`/${params.locale}/doctor-dashboard`)} className="flex items-center gap-2 font-black text-sm text-[#8f8b83] hover:text-[#141414]">
          <ArrowLeft className="size-4" /> Back to Dashboard
        </button>
        <div className="flex items-center gap-4">
          <button onClick={() => window.print()} className="no-print flex items-center gap-2 font-black text-sm px-4 py-2 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all">
            <Printer className="size-4" /> Print
          </button>
          <b className="text-xl font-black">synapse <span className="text-[#e44f2b]">ai</span></b>
        </div>
      </header>

      <section className="mx-auto max-w-[1400px] px-5 pb-16 pt-8">
        <p className="eyebrow">Patient Review</p>
        <h1 className="display text-4xl sm:text-5xl font-black">{data?.patient?.name || 'Patient'}</h1>

        <div className="mt-8 grid gap-6 lg:grid-cols-2">
          {/* Patient Info */}
          <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
            <p className="eyebrow">Patient Information</p>
            <div className="mt-4 grid gap-2 text-sm">
              <div className="flex justify-between border-b pb-2 border-[#141414]/20"><span className="font-semibold">ID:</span><span className="font-black">{data?.patient?.id}</span></div>
              <div className="flex justify-between border-b pb-2 border-[#141414]/20"><span className="font-semibold">Age:</span><span className="font-black">{data?.patient?.age}</span></div>
              <div className="flex justify-between border-b pb-2 border-[#141414]/20"><span className="font-semibold">Sex:</span><span className="font-black">{data?.patient?.sex}</span></div>
              <div className="flex justify-between"><span className="font-semibold">Phone:</span><span className="font-black">{data?.patient?.phone}</span></div>
            </div>
          </div>

          {/* Vitals */}
          {data?.patient?.vitals && (
            <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
              <p className="eyebrow">Vitals</p>
              <div className="mt-4 grid gap-2 text-sm">
                {Object.entries(JSON.parse(data.patient.vitals)).map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b pb-2 border-[#141414]/20"><span className="font-semibold capitalize">{k}:</span><span className="font-black">{String(v)}</span></div>
                ))}
              </div>
            </div>
          )}

          {/* Reports */}
          <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
            <p className="eyebrow">Medical Reports</p>
            {data?.reports?.length ? (
              <div className="mt-4 space-y-3">
                {data.reports.map((r: any, i: number) => (
                  <div key={i} className="border-2 border-[#141414] bg-[#faf8f5] p-3">
                    <p className="font-black text-sm">{r.filename}</p>
                    {r.key_points && (
                      <div className="mt-2 text-xs font-semibold text-[#8f8b83]">
                        {Array.isArray(r.key_points) ? r.key_points.slice(0, 3).map((pt: string, j: number) => <p key={j}>• {pt}</p>) : typeof r.key_points === 'object' && r.key_points.key_points ? r.key_points.key_points.slice(0, 3).map((pt: string, j: number) => <p key={j}>• {pt}</p>) : null}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : <p className="mt-4 font-semibold text-[#8f8b83]">No reports</p>}
          </div>

          {/* Visit History */}
          <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
            <p className="eyebrow">Visit History</p>
            {data?.visits?.length ? (
              <div className="mt-4 space-y-3">
                {data.visits.map((v: any, i: number) => (
                  <div key={i} className="border-2 border-[#141414] bg-[#faf8f5] p-3">
                    <p className="font-black text-sm">{new Date(v.created_at).toLocaleDateString()}</p>
                    <p className="mt-1 text-xs font-semibold text-[#48453e]">{typeof v.summary === 'string' ? v.summary : JSON.parse(v.summary)?.chief_complaint || 'No summary'}</p>
                  </div>
                ))}
              </div>
            ) : <p className="mt-4 font-semibold text-[#8f8b83]">No visits</p>}
          </div>
        </div>

        {/* Doctor Notes */}
        <div className="mt-6 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <p className="eyebrow">Doctor Notes</p>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Enter your observations and notes..."
            rows={4}
            className="mt-4 w-full border-2 border-[#141414] bg-white px-4 py-3 font-semibold outline-none focus:border-[#236b52]"
          />
        </div>

        {/* Prescription Builder */}
        <div className="mt-6 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <p className="eyebrow">Prescription Builder</p>
          
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <input value={newMed.name} onChange={e => setNewMed({ ...newMed, name: e.target.value })} placeholder="Medication name" className="border-2 border-[#141414] bg-white px-3 py-2 font-black outline-none focus:border-[#236b52]" />
            <select value={newMed.type} onChange={e => setNewMed({ ...newMed, type: e.target.value })} className="border-2 border-[#141414] bg-white px-3 py-2 font-black outline-none">
              <option value="tablet">Tablet</option>
              <option value="syrup">Syrup</option>
              <option value="injection">Injection</option>
              <option value="capsule">Capsule</option>
            </select>
            <input value={newMed.dosage} onChange={e => setNewMed({ ...newMed, dosage: e.target.value })} placeholder="Dosage (e.g., 500mg)" className="border-2 border-[#141414] bg-white px-3 py-2 font-black outline-none focus:border-[#236b52]" />
            <input value={newMed.quantity} onChange={e => setNewMed({ ...newMed, quantity: e.target.value })} placeholder="Quantity" className="border-2 border-[#141414] bg-white px-3 py-2 font-black outline-none focus:border-[#236b52]" />
            <button onClick={addMedication} className="bg-[#236b52] text-white font-black py-2 border-2 border-[#141414] hover:bg-[#1a523d] flex items-center justify-center gap-2">
              <Plus className="size-4" /> Add
            </button>
          </div>

          {medications.length > 0 && (
            <div className="mt-4 space-y-2">
              {medications.map((m, i) => (
                <div key={i} className="flex items-center justify-between border-2 border-[#141414] bg-[#faf8f5] p-3">
                  <div className="text-sm font-black">{m.name} - {m.dosage} ({m.type}) - {m.frequency}</div>
                  <button onClick={() => removeMedication(m.id)} className="text-[#e44f2b] hover:text-black p-1"><X className="size-4" /></button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Phase 9: Handwritten Report Upload */}
        <div className="mt-6 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <p className="eyebrow">Handwritten Prescription/Report Upload</p>
          <p className="mt-2 text-sm font-semibold text-[#8f8b83]">Upload handwritten prescriptions or reports for automatic text extraction</p>

          <div className="mt-4">
            <label className="flex items-center justify-center gap-3 border-2 border-dashed border-[#141414] bg-[#faf8f5] px-6 py-8 cursor-pointer hover:bg-[#f5f1e8] transition-colors">
              <Upload className="size-6 text-[#8f8b83]" />
              <span className="font-black text-[#8f8b83]">Click to upload image (JPG, PNG, WebP)</span>
              <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleHandwrittenUpload} className="hidden" />
            </label>
          </div>

          {handwrittenPreview && (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div>
                <p className="font-black text-sm mb-2">Uploaded Image</p>
                <img src={handwrittenPreview} alt="Handwritten document" className="w-full border-2 border-[#141414]" />
              </div>
              <div>
                <p className="font-black text-sm mb-2">Extracted Text</p>
                <textarea
                  value={extractedText}
                  onChange={e => setExtractedText(e.target.value)}
                  rows={10}
                  className="w-full border-2 border-[#141414] bg-white px-4 py-3 font-semibold outline-none focus:border-[#236b52] text-sm"
                  placeholder="Extracted text will appear here..."
                />
                {extracting && <p className="mt-2 text-sm font-semibold text-[#e44f2b] flex items-center gap-2"><Activity className="size-4 animate-spin" /> Extracting text...</p>}
              </div>
            </div>
          )}
        </div>

        {/* Phase 10: Diagnosis & Report Generation */}
        <div className="mt-6 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <p className="eyebrow">Diagnosis</p>
          <textarea
            value={diagnosis}
            onChange={e => setDiagnosis(e.target.value)}
            placeholder="Enter diagnosis or clinical findings..."
            rows={3}
            className="mt-4 w-full border-2 border-[#141414] bg-white px-4 py-3 font-semibold outline-none focus:border-[#236b52]"
          />

          <button
            onClick={generatePatientReport}
            disabled={generatingReport || !notes}
            className="mt-4 w-full bg-[#236b52] text-white font-black py-3 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {generatingReport ? <Activity className="size-5 animate-spin" /> : <Sparkles className="size-5" />}
            {generatingReport ? 'Generating Report...' : 'Generate Patient Report'}
          </button>

          {generatedReport && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <p className="font-black text-sm">Generated Report</p>
                <button onClick={downloadReport} className="flex items-center gap-2 text-sm font-black text-[#236b52] hover:text-[#141414]">
                  <Download className="size-4" /> Download
                </button>
              </div>
              <textarea
                value={generatedReport}
                readOnly
                rows={15}
                className="w-full border-2 border-[#141414] bg-[#faf8f5] px-4 py-3 font-semibold outline-none text-sm whitespace-pre-wrap"
              />
            </div>
          )}
        </div>

        <button onClick={savePrescription} className="mt-6 w-full bg-[#e44f2b] text-white font-black py-4 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center justify-center gap-2">
          <Save className="size-5" /> Save Prescription
        </button>

        {/* Phase 13.2: Doctor Reassignment */}
        <div className="mt-6 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <p className="eyebrow">Doctor Reassignment</p>
          <p className="mt-2 text-sm font-semibold text-[#8f8b83]">Change the assigned doctor for this patient</p>
          <button
            onClick={() => setShowReassignModal(true)}
            className="mt-4 w-full bg-[#141414] text-white font-black py-3 border-2 border-[#141414] shadow-[4px_4px_0_#e44f2b] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all flex items-center justify-center gap-2"
          >
            <RefreshCw className="size-5" /> Change Doctor
          </button>
        </div>
      </section>

      {/* Reassign Doctor Modal */}
      {showReassignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[8px_8px_0_#141414] max-w-md w-full">
            <h3 className="text-2xl font-black mb-4">Reassign Doctor</h3>
            <p className="text-sm font-semibold text-[#8f8b83] mb-4">Select a new doctor for this patient</p>
            <select
              value={selectedDoctor}
              onChange={e => setSelectedDoctor(e.target.value)}
              className="w-full border-2 border-[#141414] bg-white px-4 py-3 font-black outline-none focus:border-[#236b52] mb-4"
            >
              <option value="">Select a doctor...</option>
              {allDoctors.map((doc: any) => (
                <option key={doc.id} value={doc.id}>
                  {doc.name} - {doc.specialty}
                </option>
              ))}
            </select>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowReassignModal(false)
                  setSelectedDoctor('')
                }}
                className="flex-1 font-black py-3 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={handleReassignDoctor}
                disabled={!selectedDoctor}
                className="flex-1 bg-[#e44f2b] text-white font-black py-3 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Reassign
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
