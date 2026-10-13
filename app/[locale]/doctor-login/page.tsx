'use client'

import { useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { LogIn, ArrowLeft } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DoctorLoginPage() {
  const router = useRouter()
  const params = useParams()
  const t = useTranslations('doctor')
  const [doctorId, setDoctorId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = () => {
    if (!doctorId.trim()) return setError('Please enter Doctor ID')
    setLoading(true)
    setError('')
    fetch(`${API}/doctors/login?doctor_id=${encodeURIComponent(doctorId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
      .then(r => {
        if (!r.ok) throw new Error('Doctor not found')
        return r.json()
      })
      .then(data => {
        localStorage.setItem('doctor', JSON.stringify(data))
        router.push(`/${params.locale}/doctor-dashboard`)
      })
      .catch(() => setError('Login failed - Invalid Doctor ID'))
      .finally(() => setLoading(false))
  }

  return (
    <main className="min-h-screen bg-[#f5f1e8] flex items-center justify-center px-5">
      <div className="w-full max-w-md panel border-2 border-[#141414] bg-white p-8 shadow-[8px_8px_0_#141414]">
        <button onClick={() => router.push(`/${params.locale}`)} className="flex items-center gap-2 font-black text-sm text-[#8f8b83] hover:text-[#141414] mb-6">
          <ArrowLeft className="size-4" /> Back to Home
        </button>
        <p className="eyebrow">Doctor Portal</p>
        <h1 className="display text-4xl font-black mt-2">Login</h1>
        <p className="mt-4 font-semibold text-[#48453e]">Enter your Doctor ID to access the dashboard</p>

        <div className="mt-8">
          <label className="block text-sm font-black mb-2">Doctor ID</label>
          <input
            value={doctorId}
            onChange={e => setDoctorId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLogin()}
            placeholder="e.g., DOC-001"
            className="w-full border-2 border-[#141414] bg-white px-4 py-3 font-black outline-none focus:border-[#236b52]"
          />
          {error && <p className="mt-2 text-xs text-[#e44f2b] font-bold">{error}</p>}
        </div>

        <button onClick={handleLogin} disabled={loading} className="mt-6 w-full bg-[#e44f2b] text-white font-black py-4 border-2 border-[#141414] shadow-[4px_4px_0_#141414] disabled:opacity-50 hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all">
          {loading ? 'Logging in...' : <span className="flex items-center justify-center gap-2"><LogIn className="size-5" /> Login</span>}
        </button>

        <div className="mt-6 p-4 bg-[#b9dbcb] border-2 border-[#141414] text-xs font-semibold">
          <p className="font-black uppercase text-[#236b52] mb-2">Test Doctor IDs:</p>
          <p>DOC-001: Dr. Anus Kumar (Cardiology)</p>
          <p>DOC-002: Dr. Priya Sharma (General Medicine)</p>
          <p>DOC-003: Dr. Rajesh Gupta (Pediatrics)</p>
        </div>
      </div>
    </main>
  )
}
