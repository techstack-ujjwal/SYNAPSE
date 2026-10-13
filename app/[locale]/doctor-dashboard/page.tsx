'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { LogOut, Users, RefreshCw, CheckCircle, Clock, AlertCircle, FileText } from 'lucide-react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DoctorDashboard() {
  const router = useRouter()
  const params = useParams()
  const [doctor, setDoctor] = useState<any>(null)
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const doc = localStorage.getItem('doctor')
    if (!doc) {
      router.push(`/${params.locale}/doctor-login`)
      return
    }
    try {
      const docData = JSON.parse(doc)
      if (!docData || !docData.id) {
        localStorage.removeItem('doctor')
        router.push(`/${params.locale}/doctor-login`)
        return
      }
      setDoctor(docData)
      fetch(`${API}/doctors/${docData.id}/patients`)
        .then(r => r.json())
        .then(data => {
          console.log('Patients data:', data)
          setPatients(Array.isArray(data) ? data : [])
        })
        .catch(err => {
          console.error('Error fetching patients:', err)
          setPatients([])
        })
        .finally(() => setLoading(false))
    } catch (err) {
      console.error('Error parsing doctor data:', err)
      localStorage.removeItem('doctor')
      router.push(`/${params.locale}/doctor-login`)
    }
  }, [router, params.locale])

  const handleLogout = () => {
    localStorage.removeItem('doctor')
    router.push(`/${params.locale}/doctor-login`)
  }

  const updateStatus = (queueId: number, status: string) => {
    fetch(`${API}/queue/${queueId}/status`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
      .then(() => setPatients(p => p.map(x => x.id === queueId ? { ...x, status } : x)))
      .catch(() => {})
  }

  if (loading) return <div className="min-h-screen bg-[#f5f1e8] flex items-center justify-center"><RefreshCw className="size-8 animate-spin text-[#e44f2b]" /></div>

  return (
    <main className="min-h-screen bg-[#f5f1e8]">
      <header className="flex items-center justify-between px-5 py-5 lg:px-10 border-b-2 border-[#141414] bg-white">
        <div>
          <b className="text-xl font-black">synapse <span className="text-[#e44f2b]">ai</span></b>
          <p className="text-sm font-semibold text-[#8f8b83] mt-1">{doctor?.name} • {doctor?.specialty}</p>
        </div>
        <button onClick={handleLogout} className="flex items-center gap-2 font-black px-4 py-2 border-2 border-[#141414] bg-white hover:bg-[#f5f1e8] transition-all">
          <LogOut className="size-4" /> Logout
        </button>
      </header>

      <section className="mx-auto max-w-[1400px] px-5 pb-16 pt-8">
        <p className="eyebrow">Doctor Dashboard</p>
        <h1 className="display text-4xl sm:text-5xl font-black">Your Patients</h1>

        <div className="mt-8 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
          <div className="flex items-center justify-between border-b-2 border-[#141414] pb-4 mb-4">
            <div className="flex items-center gap-4">
              <Users className="size-5 text-[#236b52]" />
              <p className="font-black text-lg">Patient Queue</p>
            </div>
            <p className="text-sm font-bold text-[#8f8b83]">{patients.length} patients</p>
          </div>

          {patients.length === 0 ? (
            <div className="bg-[#f5f1e8] border-2 border-[#141414] p-8 text-center">
              <Users className="size-12 mx-auto text-[#8f8b83] mb-4" />
              <p className="font-black text-lg text-[#8f8b83]">No patients in queue</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-[#141414]">
                    <th className="text-left font-black text-sm py-3 px-2">Token</th>
                    <th className="text-left font-black text-sm py-3 px-2">Patient</th>
                    <th className="text-left font-black text-sm py-3 px-2">Priority</th>
                    <th className="text-left font-black text-sm py-3 px-2">Status</th>
                    <th className="text-left font-black text-sm py-3 px-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {patients.map(p => (
                    <tr key={p.id} className="border-b border-[#141414]/20">
                      <td className="py-3 px-2 font-black">{p.token}</td>
                      <td className="py-3 px-2 font-semibold">{p.patient_name}</td>
                      <td className="py-3 px-2">
                        <span className={`px-2 py-1 text-xs font-black ${p.priority === 'high' ? 'bg-[#e44f2b] text-white' : p.priority === 'low' ? 'bg-[#236b52] text-white' : 'bg-[#f5cf4a] text-black'}`}>
                          {p.priority}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <span className="flex items-center gap-1 text-sm font-semibold">
                          {p.status === 'completed' ? <CheckCircle className="size-4 text-[#236b52]" /> : p.status === 'in_consultation' ? <Clock className="size-4 text-[#f57c00]" /> : <AlertCircle className="size-4 text-[#8f8b83]" />}
                          {p.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="py-3 px-2">
                        <button onClick={() => router.push(`/${params.locale}/doctor-dashboard/review/${p.patient_id}`)} className="bg-[#236b52] text-white px-3 py-1 text-xs font-black border-2 border-[#141414] hover:bg-[#1a523d] transition-all mr-2">
                          Review
                        </button>
                        {p.status === 'waiting' && (
                          <button onClick={() => updateStatus(p.id, 'in_consultation')} className="bg-[#f5cf4a] text-black px-3 py-1 text-xs font-black border-2 border-[#141414] hover:bg-[#e6b833] transition-all">
                            Start
                          </button>
                        )}
                        {p.status === 'in_consultation' && (
                          <button onClick={() => updateStatus(p.id, 'completed')} className="bg-[#e44f2b] text-white px-3 py-1 text-xs font-black border-2 border-[#141414] hover:bg-[#c93f1d] transition-all">
                            Complete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </main>
  )
}
