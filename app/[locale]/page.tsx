'use client'

import { ChangeEvent, useState, useEffect, useRef } from 'react'
import {
  ArrowLeft, ArrowRight, Check, FileText, Languages,
  LogOut, Mic, MicOff, Plus, ScanFace, Send, Upload, Volume2, VolumeX, X,
  AlertCircle, CheckCircle2, Sparkles, Activity, Users, RefreshCw, Clock
} from 'lucide-react'
import { ParameterCard } from '@/components/ui/parameter-card'
import { ReportComparison } from '@/components/ui/report-comparison'
import { QRCodeSVG } from 'qrcode.react'
import { useParams, useRouter, usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { localeNames, languageToLocale, Locale, defaultLocale } from '@/i18n/request'
import { browserSpeechSupported, speakInBrowser, startBrowserRecognition } from '@/lib/speech'

type Mode = 'landing' | 'register' | 'returning' | 'dashboard'
type DashboardSection = 'overview' | 'records' | 'reports' | 'prescriptions' | 'visits'
type Step = 1 | 2 | 3 | 4
type Form = { name: string; age: string; phone: string; sex: string; bp: string; sugar: string; weight: string; height: string; temperature: string }
type Report = { id: number; name: string; size: string; file?: File; key_points?: string[] }
type Message = { from: 'ai' | 'user'; text: string }

const languageList = Object.values(localeNames)
const stepsKeys = ['step1', 'step2', 'step3', 'step4'] as const
const blank: Form = { name:'', age:'', phone:'', sex:'', bp:'', sugar:'', weight:'', height:'', temperature:'' }
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
let MAX_QUESTIONS = 8

export default function Page() {
  const params = useParams()
  const router = useRouter()
  const currentLocale = ((params?.locale as string) || defaultLocale) as Locale

  // next-intl translation hooks
  const tCommon = useTranslations('common')
  const tHeader = useTranslations('header')
  const tLanding = useTranslations('landing')
  const tReg = useTranslations('registration')
  const tConv = useTranslations('conversation')
  const tSum = useTranslations('summary')
  const tToken = useTranslations('token')
  const tRet = useTranslations('returning')
  const tDash = useTranslations('dashboard')
  const tVal = useTranslations('validation')

  const [mode, setMode] = useState<Mode>('landing')
  const [step, setStep] = useState<Step>(1)
  const [language, setLanguage] = useState<string>(localeNames[currentLocale] || 'English')
  const [form, setForm] = useState<Form>(blank)
  const [errors, setErrors] = useState<Record<string, string>>({ report: '' })
  const [reports, setReports] = useState<Report[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [chatValue, setChatValue] = useState('')
  const [symptoms, setSymptoms] = useState<string[]>([])
  const [patientId, setPatientId] = useState('')
  const [lookup, setLookup] = useState('')
  const [status, setStatus] = useState('')
  const [token, setToken] = useState('')
  const [queue, setQueue] = useState({ people_ahead: 0, estimated_minutes: 0, priority: 'medium' })
  const [summary, setSummary] = useState<any>(null)
  const [listening, setListening] = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [questionCount, setQuestionCount] = useState(0)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [whisperEnabled, setWhisperEnabled] = useState(true)
  const [ttsEnabled, setTtsEnabled] = useState(true)

  // Report comparison state
  const [showComparison, setShowComparison] = useState(false)
  const [comparisonData, setComparisonData] = useState<any>(null)
  const [pastReportId, setPastReportId] = useState<number | null>(null)
  const [presentReportId, setPresentReportId] = useState<number | null>(null)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const browserRecognitionRef = useRef<{ stop: () => void } | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  // Sync language display name with current URL locale
  useEffect(() => {
    if (currentLocale && localeNames[currentLocale]) {
      setLanguage(localeNames[currentLocale])
    }
  }, [currentLocale])

  // Fetch configuration from backend on mount
  useEffect(() => {
    fetch(`${API}/config`)
      .then(x => x.json())
      .then(config => {
        MAX_QUESTIONS = config.max_questions || 8
        setWhisperEnabled(!!config.whisper_enabled)
        setTtsEnabled(!!config.tts_enabled)
      })
      .catch(() => {
        setWhisperEnabled(false)
        setTtsEnabled(false)
      })
  }, [])

  const handleLanguageChange = (newLanguageName: string) => {
    setLanguage(newLanguageName)
    const targetLocale = languageToLocale[newLanguageName] || defaultLocale
    router.replace(`/${targetLocale}`)
  }

  const update = (key: keyof Form, value: string) => {
    setForm(f => ({ ...f, [key]: value }))
    setErrors(e => ({ ...e, [key]: '' }))
  }

  const validate = () => {
    const e: Record<string, string> = {}
    if (!/^[\p{L} .'-]{2,60}$/u.test(form.name.trim())) e.name = tVal('validName')
    if (!/^\d{1,3}$/.test(form.age) || +form.age > 120) e.age = tVal('validAge')
    if (!/^(?:\+91[6-9]\d{9}|[6-9]\d{9})$/.test(form.phone.replace(/[\s-]/g, ''))) e.phone = tVal('validPhone')
    if (!form.sex) e.sex = tVal('selectOption')
    if (form.bp && !/^\d{2,3}\/\d{2,3}$/.test(form.bp)) e.bp = tVal('validBP')
    
    const numericKeys: (keyof Form)[] = ['sugar', 'weight', 'height', 'temperature']
    numericKeys.forEach(k => {
      if (form[k] && !/^\d+(\.\d+)?$/.test(form[k])) e[k] = tVal('numbersOnly')
    })

    setErrors(e)
    return Object.keys(e).length === 0
  }

  const addReport = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const maxSize = 5 * 1024 * 1024 // 5MB in bytes
    if (file.size > maxSize) {
      setErrors(err => ({ ...err, report: tReg('fileSizeExceeded') }))
      e.target.value = ''
      return
    }

    if (file.type !== 'application/pdf' && !file.type.startsWith('image/')) {
      setErrors(err => ({ ...err, report: tReg('invalidFileType') }))
      e.target.value = ''
      return
    }

    if (patientId) {
      setStatus(tSum('extractingReport'))
      const formData = new FormData()
      formData.append('report', file)

      try {
        const res = await fetch(`${API}/patients/${patientId}/reports`, {
          method: 'POST',
          body: formData
        }).then(x => x.json())

        if (res.ok) {
          setReports(r => [...r, {
            id: res.report_id || Date.now(),
            name: file.name,
            size: `${Math.ceil(file.size / 1024)} KB`,
            key_points: res.key_points || []
          }])
          setErrors(err => ({ ...err, report: '' }))
        } else {
          setErrors(err => ({ ...err, report: res.error || tReg('uploadFailed') }))
        }
      } catch (err) {
        setErrors(err => ({ ...err, report: tReg('uploadFailed') }))
      }
      setStatus('')
    } else {
      setReports(r => [...r, {
        id: Date.now(),
        name: file.name,
        size: `${Math.ceil(file.size / 1024)} KB`,
        file
      }])
      setErrors(err => ({ ...err, report: '' }))
    }

    e.target.value = ''
  }

  const start = async () => {
    if (!validate()) return
    setStatus(tConv('creatingRecord'))

    const r = await fetch(`${API}/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        age: +form.age,
        vitals: {
          bp: form.bp,
          sugar: form.sugar,
          weight: form.weight,
          height: form.height,
          temperature: form.temperature
        }
      })
    }).then(x => x.json()).catch(() => ({ patient_id: `SYN-${Date.now()}` }))

    setPatientId(r.patient_id)

    // Fetch initial hardcoded greeting in the chosen language (Requirement 3)
    setStatus(tConv('connecting'))
    const aiResponse = await fetch(`${API}/conversation/initial?patient_id=${r.patient_id}&language=${encodeURIComponent(language)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: r.patient_id, language })
    })
      .then(x => x.json())
      .catch(() => ({
        question: language === 'मारवाड़ी' 
          ? 'राम राम सा! म्हे थारी मदद सारू हाजर हां। आज थारी तबीयत कियां है?' 
          : 'Hello, I am here to help you. How are you feeling today?'
      }))

    setMessages([{ from: 'ai', text: aiResponse.question }])
    setQuestionCount(0)
    setStatus('')

    // Auto-play greeting voice (Requirement 5)
    if (aiResponse.question) {
      playAiAudio(aiResponse.question)
    }

    // Upload pending reports
    const pendingReports = reports.filter(rep => rep.file)
    for (const report of pendingReports) {
      if (report.file) {
        const formData = new FormData()
        formData.append('report', report.file)
        try {
          const uploaded = await fetch(`${API}/patients/${r.patient_id}/reports`, {
            method: 'POST',
            body: formData
          }).then(x => x.json())

          if (uploaded.ok) {
            setReports(prev => prev.map(item => item.id === report.id ? {
              ...item,
              key_points: uploaded.key_points || []
            } : item))
          }
        } catch (err) {
          console.error('Failed to upload report:', err)
        }
      }
    }

    setReports(r => r.map(rep => ({ ...rep, file: undefined })))
    setStep(2)
  }

  const send = async () => {
    const text = chatValue.trim()
    if (!text) return
    setChatValue('')
    setMessages(m => [...m, { from: 'user', text }])
    setStatus(tConv('synapseThinking'))

    const r = await fetch(`${API}/conversation/next`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        message: text,
        language,
        history: [...messages, { from: 'user', text }].map(m => ({
          role: m.from === 'user' ? 'user' : 'ai',
          from: m.from,
          text: m.text
        }))
      })
    }).then(x => x.json()).catch(() => ({
      question: language === 'मारवाड़ी'
        ? 'राम राम सा, थारी बीमारी रा लक्षण और बताओ।'
        : 'Please continue describing what you are feeling.',
      language
    }))

    setMessages(m => [...m, { from: 'ai', text: r.question }])
    setSymptoms(s => Array.from(new Set([...s, ...(r.symptoms || [])])))
    setQuestionCount(c => c + 1)
    setStatus('')

    // Play AI audio voice reply in patient's language (Requirement 5)
    if (r.question) {
      playAiAudio(r.question)
    }
  }

  // Voice recording toggle with intelligent fallback (Browser Speech → OpenAI Whisper)
  const toggleVoice = async () => {
    if (listening) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop()
      }
      browserRecognitionRef.current?.stop()
      browserRecognitionRef.current = null
      setListening(false)
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }

    // Try browser speech first (free, no tokens)
    if (browserSpeechSupported()) {
      setListening(true)
      setStatus(tConv('listening'))
      const recognition = startBrowserRecognition(language, (text) => {
        setChatValue(v => (v ? `${v} ${text}` : text).trim())
        setStatus('')
      }, () => {
        setListening(false)
        browserRecognitionRef.current = null
      })
      browserRecognitionRef.current = recognition
      return
    }

    // Fallback to OpenAI Whisper if browser speech not supported
    if (!whisperEnabled) {
      setStatus(tConv('voiceNotSupported'))
      return
    }

    try {
      setStatus(tConv('accessingMic'))
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
        ? 'audio/webm;codecs=opus' 
        : (MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : 'audio/webm')

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder
      audioChunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        stream.getTracks().forEach(track => track.stop())
        if (timerRef.current) clearInterval(timerRef.current)
        setRecordingSeconds(0)

        const reader = new FileReader()
        reader.readAsDataURL(audioBlob)
        reader.onloadend = async () => {
          const base64Audio = reader.result as string
          const base64Data = base64Audio.split(',')[1]

          setStatus('Transcribing with OpenAI Whisper…')
          try {
            const response = await fetch(`${API}/audio/transcribe`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ audio_data: base64Data, language })
            })
            const result = await response.json()

            if (result.text) {
              setChatValue(v => (v ? `${v} ${result.text}` : result.text).trim())
              setStatus('')
            } else {
              setStatus(result.error || 'No speech detected. Please try again.')
            }
          } catch (err) {
            setStatus('Transcription failed. Please check network/API.')
          }
        }
      }

      recorder.start(250) // slice chunks every 250ms
      setListening(true)
      setRecordingSeconds(0)
      setStatus('Listening… Speak now in your language')

      timerRef.current = setInterval(() => {
        setRecordingSeconds(s => {
          if (s >= 15) {
            if (recorder.state === 'recording') recorder.stop()
            setListening(false)
            if (timerRef.current) clearInterval(timerRef.current)
            return 0
          }
          return s + 1
        })
      }, 1000)

    } catch (err) {
      setStatus('Microphone access denied or unavailable.')
      console.error(err)
    }
  }

  // Play AI TTS Audio with natural regional accent (Requirement 5)
  const playAiAudio = async (text: string) => {
    try {
      setIsPlayingAudio(true)
      const response = await fetch(`${API}/audio/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language, voice: 'nova' })
      })
      const result = await response.json()

      if (result.audio && audioRef.current) {
        const audioData = `data:audio/mp3;base64,${result.audio}`
        audioRef.current.src = audioData
        audioRef.current.onended = () => setIsPlayingAudio(false)
        audioRef.current.onerror = () => setIsPlayingAudio(false)
        await audioRef.current.play()
      } else {
        setIsPlayingAudio(false)
      }
    } catch (err) {
      console.error('TTS playback error:', err)
      setIsPlayingAudio(false)
    }
  }

  // Prepare Summary with English handoff and Report Key Points (Requirement 4)
  const makeSummary = async () => {
    setStatus('Preparing clinician summary and analyzing attached reports…')
    const r = await fetch(`${API}/summary`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id: patientId,
        form,
        messages,
        reports,
        symptoms,
        language
      })
    }).then(x => x.json()).catch(() => ({
      summary: {
        chief_complaint: 'Medical intake summary recorded.',
        timeline: 'Recent onset',
        relevant_vitals: form,
        report_findings: { pain_nature: 'Reported', pain_triggers: 'None', associated_symptoms: symptoms.join(', ') },
        red_flags: [],
        missing_information: [],
        recommended_specialty: 'General Medicine',
        risk: 'medium'
      },
      risk: 'medium',
      priority: 'medium',
      report_key_points: []
    }))

    setSummary(r)
    setStatus('')
    setStep(3)
  }

  const makeToken = async () => {
    const priority = summary?.priority || 'medium'
    const r = await fetch(`${API}/queue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId, priority })
    }).then(x => x.json()).catch(() => ({
      token: `S-${Date.now()}`,
      priority: 'medium',
      status: 'waiting'
    }))

    setToken(r.token)
    setQueue({ ...queue, priority: r.priority })
    setStep(4)
  }

  if (mode === 'dashboard') {
    return (
      <Dashboard 
        patientId={lookup} 
        tDash={tDash}
        onNew={() => {
          setPatientId(lookup)
          setMode('register')
          setStep(2)
          fetch(`${API}/conversation/initial?patient_id=${lookup}&language=${encodeURIComponent(language)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patient_id: lookup, language })
          })
            .then(x => x.json())
            .then(res => setMessages([{ from: 'ai', text: res.question }]))
            .catch(() => setMessages([{ from: 'ai', text: 'Hello, how can I help you today?' }]))
        }} 
        onLogout={() => setMode('landing')}
      />
    )
  }

  return (
    <main className="min-h-screen bg-[#f5f1e8] text-[#141414]">
      <audio ref={audioRef} className="hidden" />

      {/* Global Header with Language Switcher */}
      <Header 
        language={language} 
        onLanguageChange={handleLanguageChange}
        tHeader={tHeader}
        isPlayingAudio={isPlayingAudio}
      />

      {mode === 'landing' ? (
        <Landing 
          tLanding={tLanding}
          router={router}
          currentLocale={currentLocale}
          onNew={() => {
            setMode('register')
            setForm(blank)
            setStep(1)
            setPatientId('')
            setMessages([])
            setSymptoms([])
            setQuestionCount(0)
          }} 
          onReturning={() => setMode('returning')}
        />
      ) : mode === 'returning' ? (
        <Returning 
          lookup={lookup} 
          setLookup={setLookup} 
          tRet={tRet}
          tCommon={tCommon}
          onBack={() => setMode('landing')} 
          onOpen={() => { if (lookup.trim()) setMode('dashboard') }}
        />
      ) : (
        <section className="mx-auto max-w-[1180px] px-5 pb-16 pt-8 lg:px-10">
          <div className="mb-6 flex justify-between items-end">
            <div>
              <p className="eyebrow">{step === 2 ? tConv('eyebrow') : tReg('eyebrow')}</p>
              <h1 className="display text-4xl sm:text-5xl font-black">
                {step === 2 ? tConv('title') : tReg('title')}
              </h1>
            </div>
            <b className="text-3xl font-black">{step}/4</b>
          </div>

          <Rail step={step} tLanding={tLanding} />

          {step === 1 && (
            <Details 
              form={form} 
              errors={errors} 
              update={update} 
              reports={reports} 
              addReport={addReport} 
              removeReport={id => setReports(r => r.filter(x => x.id !== id))} 
              onNext={start}
              tReg={tReg}
            />
          )}

          {step === 2 && (
            <Chat 
              messages={messages} 
              value={chatValue} 
              setValue={setChatValue} 
              symptoms={symptoms} 
              listening={listening} 
              recordingSeconds={recordingSeconds}
              onVoice={toggleVoice} 
              onSend={send} 
              onBack={() => setStep(1)} 
              onNext={makeSummary} 
              questionCount={questionCount} 
              playAiAudio={playAiAudio}
              isPlayingAudio={isPlayingAudio}
              tConv={tConv}
              tCommon={tCommon}
            />
          )}

          {step === 3 && (
            <Summary
              name={form.name}
              id={patientId}
              data={summary}
              reports={reports}
              form={form}
              onBack={() => setStep(2)}
              onNext={makeToken}
              playAiAudio={playAiAudio}
              tSum={tSum}
              tCommon={tCommon}
              language={language}
            />
          )}

          {step === 4 && (
            <Token 
              token={token} 
              id={patientId} 
              queue={queue} 
              name={form.name} 
              onBack={() => setStep(3)} 
              onDone={() => setMode('dashboard')}
              tToken={tToken}
              tCommon={tCommon}
            />
          )}

          {status && (
            <div className="mt-4 flex items-center gap-2 p-3 bg-white border-2 border-[#141414] shadow-[4px_4px_0_#141414]">
              <Activity className="size-4 animate-spin text-[#e44f2b]" />
              <p className="text-sm font-black text-[#e44f2b]">{status}</p>
            </div>
          )}
        </section>
      )}
    </main>
  )
}

function Header({ language, onLanguageChange, tHeader, isPlayingAudio }: { 
  language: string; 
  onLanguageChange: (v: string) => void;
  tHeader: any;
  isPlayingAudio: boolean;
}) {
  return (
    <header className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-5 lg:px-10 border-b-2 border-[#141414]">
      <div className="flex items-center gap-3">
        <b className="text-2xl font-black tracking-tight">synapse <span className="text-[#e44f2b]">ai</span></b>
        {isPlayingAudio && (
          <span className="flex items-center gap-1 bg-[#236b52] text-white text-xs px-2 py-1 rounded font-bold animate-pulse">
            <Volume2 className="size-3" /> Voice Active
          </span>
        )}
      </div>

      <label className="flex items-center gap-2 border-2 border-[#141414] bg-white px-3 py-2 text-xs font-black uppercase shadow-[3px_3px_0_#141414] hover:shadow-[1px_1px_0_#141414] transition-all">
        <Languages className="size-4 text-[#e44f2b]" />
        <span className="hidden sm:inline font-bold text-[#8f8b83]">{tHeader('language')}:</span>
        <select 
          aria-label={tHeader('language')} 
          value={language} 
          onChange={e => onLanguageChange(e.target.value)} 
          className="bg-transparent font-black outline-none cursor-pointer"
        >
          {languageList.map(name => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </label>
    </header>
  )
}

function Landing({ onNew, onReturning, tLanding, router, currentLocale }: { onNew: () => void; onReturning: () => void; tLanding: any; router: any; currentLocale: string }) {
  return (
    <section className="mx-auto grid max-w-[1440px] gap-10 px-5 pb-16 pt-16 lg:grid-cols-[1fr_.8fr] lg:px-10">
      <div>
        <p className="eyebrow">{tLanding('eyebrow')}</p>
        <h1 className="display max-w-3xl text-5xl sm:text-7xl font-black">
          {tLanding('title')}
        </h1>
        <p className="mt-8 max-w-xl text-lg font-semibold leading-relaxed text-[#48453e]">
          {tLanding('description')}
        </p>
        <div className="mt-10 grid max-w-xl gap-4 sm:grid-cols-2">
          <button onClick={onNew} className="action bg-[#e44f2b] text-white flex items-center justify-center gap-2 font-black py-4 px-6 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all">
            {tLanding('newPatient')} <ArrowRight className="size-5" />
          </button>
          <button onClick={onReturning} className="action bg-white flex items-center justify-center gap-2 font-black py-4 px-6 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all">
            {tLanding('returningPatient')} <ScanFace className="size-5" />
          </button>
        </div>
        <div className="mt-4">
          <button onClick={() => router.push(`/${currentLocale}/doctor-login`)} className="text-sm font-semibold text-[#8f8b83] hover:text-[#e44f2b] transition-colors">
            Doctor Login →
          </button>
        </div>
      </div>
      <div className="grid min-h-[410px] place-items-center border-2 border-[#141414] bg-[#b9dbcb] p-6 shadow-[8px_8px_0_#141414]">
        <div className="w-full border-2 border-[#141414] bg-white p-7 shadow-[5px_5px_0_#141414]">
          <p className="eyebrow">{tLanding('firstStep')}</p>
          <p className="mt-4 text-4xl font-black leading-tight">
            {tLanding('oneConversation')}<br />{tLanding('clearerVisit')}
          </p>
          <div className="mt-8 grid gap-3 text-sm font-black">
            <p className="flex items-center gap-2"><CheckCircle2 className="size-4 text-[#236b52]" /> {tLanding('step1')}</p>
            <p className="flex items-center gap-2"><CheckCircle2 className="size-4 text-[#236b52]" /> {tLanding('step2')}</p>
            <p className="flex items-center gap-2"><CheckCircle2 className="size-4 text-[#236b52]" /> {tLanding('step3')}</p>
          </div>
        </div>
      </div>
    </section>
  )
}

function Rail({ step, tLanding }: { step: Step; tLanding: any }) {
  const stepLabels = [
    tLanding('step1') || '01 — Details',
    tLanding('step2') || '02 — Conversation',
    tLanding('step3') || '03 — Summary',
    '04 — Token & Queue'
  ]

  return (
    <div className="mb-7 grid grid-cols-4 gap-2 border-y-2 border-[#141414] py-4 bg-white/50">
      {stepLabels.map((label, i) => (
        <div 
          key={i} 
          className={`flex items-center gap-2 text-xs font-black uppercase ${
            step === i + 1 ? 'text-[#e44f2b]' : step > i + 1 ? 'text-[#236b52]' : 'text-[#8f8b83]'
          }`}
        >
          <span className="grid size-7 shrink-0 place-items-center border-2 border-current font-black">
            {step > i + 1 ? <Check className="size-4" /> : i + 1}
          </span>
          <span className="hidden sm:inline truncate">{label}</span>
        </div>
      ))}
    </div>
  )
}

function Field({ 
  label, id, value, update, error, required, type = 'text', placeholder 
}: { 
  label: string; id: keyof Form; value: string; update: (k: keyof Form, v: string) => void; 
  error?: string; required?: boolean; type?: string; placeholder?: string 
}) {
  return (
    <label className="flex flex-col gap-2 text-sm font-black">
      <span>{label}{required && <span className="text-[#e44f2b]"> *</span>}</span>
      <input 
        id={id} 
        type={type} 
        value={value} 
        placeholder={placeholder} 
        onChange={e => update(id, e.target.value)} 
        aria-invalid={!!error} 
        className={`border-2 bg-white px-3 py-3 font-semibold outline-none transition-colors ${
          error ? 'border-[#e44f2b] bg-[#fff3ef]' : 'border-[#141414] focus:border-[#236b52]'
        }`}
      />
      {error && <span className="text-xs text-[#e44f2b] font-bold">{error}</span>}
    </label>
  )
}

function Details({ 
  form, errors, update, reports, addReport, removeReport, onNext, tReg 
}: { 
  form: Form; errors: Record<string, string>; update: (k: keyof Form, v: string) => void; 
  reports: Report[]; addReport: (e: ChangeEvent<HTMLInputElement>) => Promise<void>; 
  removeReport: (id: number) => void; onNext: () => void; tReg: any 
}) {
  const vitalsConfig: [keyof Form, string, string][] = [
    ['bp', tReg('bloodPressure'), '120/80'],
    ['sugar', tReg('bloodSugar'), 'mg/dL'],
    ['weight', tReg('weight'), 'kg'],
    ['height', tReg('height'), 'cm'],
    ['temperature', tReg('temperature'), '°C']
  ]

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
        <h2 className="text-3xl font-black">{tReg('tellUsAboutYou')}</h2>
        
        <div className="mt-7 grid gap-5 sm:grid-cols-2">
          <Field 
            label={tReg('fullName')} 
            id="name" 
            value={form.name} 
            update={update} 
            error={errors.name} 
            required 
            placeholder="John Doe" 
          />
          <Field 
            label={tReg('age')} 
            id="age" 
            type="number" 
            value={form.age} 
            update={update} 
            error={errors.age} 
            required 
            placeholder="35" 
          />
          <Field 
            label={tReg('phoneNumber')} 
            id="phone" 
            value={form.phone} 
            update={update} 
            error={errors.phone} 
            required 
            placeholder="9876543210" 
          />
          <label className="flex flex-col gap-2 text-sm font-black">
            <span>{tReg('sex')} *</span>
            <select 
              value={form.sex} 
              onChange={e => update('sex', e.target.value)} 
              className={`border-2 bg-white px-3 py-3 font-semibold outline-none ${
                errors.sex ? 'border-[#e44f2b]' : 'border-[#141414]'
              }`}
            >
              <option value="">{tReg('selectSex')}</option>
              <option value="Female">{tReg('female')}</option>
              <option value="Male">{tReg('male')}</option>
              <option value="Intersex">{tReg('intersex')}</option>
              <option value="Prefer not to say">{tReg('preferNotToSay')}</option>
            </select>
            {errors.sex && <span className="text-xs text-[#e44f2b] font-bold">{errors.sex}</span>}
          </label>
        </div>

        <p className="eyebrow mt-8">{tReg('optionalVitals')}</p>
        <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {vitalsConfig.map(([id, label, placeholder]) => (
            <Field 
              key={id} 
              label={label} 
              id={id} 
              value={form[id]} 
              update={update} 
              error={errors[id]} 
              placeholder={placeholder} 
            />
          ))}
        </div>

        <button 
          onClick={onNext} 
          className="mt-8 action w-full bg-[#141414] text-white flex items-center justify-center gap-2 font-black py-4 px-6 border-2 border-[#141414] shadow-[4px_4px_0_#e44f2b] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
        >
          {tReg('continueToConversation')} <ArrowRight className="size-5" />
        </button>
      </div>

      <aside className="panel h-fit bg-[#f5cf4a] border-2 border-[#141414] p-6 shadow-[6px_6px_0_#141414]">
        <div className="flex items-center justify-between">
          <div>
            <p className="eyebrow">{tReg('documents')}</p>
            <h3 className="text-2xl font-black">{tReg('pastReports')}</h3>
          </div>
          <label className="cursor-pointer rounded border-2 border-[#141414] bg-white px-3 py-2 text-xs font-black hover:bg-[#141414] hover:text-white transition-colors shadow-[2px_2px_0_#141414]">
            <Upload className="mr-1 inline size-4" /> {tReg('upload')}
            <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png,.webp" onChange={addReport} />
          </label>
        </div>

        {errors.report && <p className="mt-2 text-xs text-[#e44f2b] font-bold">{errors.report}</p>}

        <div className="mt-4 space-y-2">
          {reports.length === 0 ? (
            <p className="text-sm font-semibold text-[#8f8b83] bg-white/60 p-3 border border-[#141414]">
              {tReg('noReports')}
            </p>
          ) : (
            reports.map(r => (
              <div key={r.id} className="flex items-center justify-between border-2 border-[#141414] bg-white px-3 py-2">
                <div className="flex items-center gap-2 truncate">
                  <FileText className="size-4 shrink-0 text-[#236b52]" />
                  <span className="text-sm font-bold truncate">{r.name}</span>
                  <span className="text-xs text-[#8f8b83] shrink-0">({r.size})</span>
                </div>
                <button onClick={() => removeReport(r.id)} className="text-[#e44f2b] hover:text-black p-1">
                  <X className="size-4" />
                </button>
              </div>
            ))
          )}
        </div>
        <p className="mt-3 text-xs font-semibold text-[#48453e]">{tReg('maxFileSize')}</p>
      </aside>
    </div>
  )
}

function Chat({ 
  messages, value, setValue, symptoms, listening, recordingSeconds, onVoice, onSend, onBack, onNext, 
  questionCount, playAiAudio, isPlayingAudio, tConv, tCommon 
}: { 
  messages: Message[]; value: string; setValue: (v: string) => void; symptoms: string[]; 
  listening: boolean; recordingSeconds: number; onVoice: () => void; onSend: () => void; 
  onBack: () => void; onNext: () => void; questionCount: number; 
  playAiAudio: (text: string) => void; isPlayingAudio: boolean; tConv: any; tCommon: any 
}) {
  const userMessages = messages.filter(m => m.from === 'user').length
  const shouldAdvance = questionCount >= MAX_QUESTIONS

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="panel p-0 border-2 border-[#141414] bg-white shadow-[6px_6px_0_#141414] overflow-hidden flex flex-col justify-between">
        <div className="border-b-2 border-[#141414] bg-[#b9dbcb] p-5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-black">{tConv('talkWithSynapse')}</h2>
              <p className="text-sm font-bold">{tConv('adaptiveFollowUp')}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-black uppercase">{tConv('questions')}</p>
              <p className="text-2xl font-black">{questionCount}/{MAX_QUESTIONS}</p>
            </div>
          </div>
        </div>

        {/* Message Thread */}
        <div className="flex min-h-[380px] max-h-[500px] overflow-y-auto flex-col gap-4 p-5 bg-[#faf8f5]">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.from === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div 
                className={`max-w-[85%] border-2 border-[#141414] px-4 py-3 font-semibold shadow-[3px_3px_0_#141414] ${
                  m.from === 'user' ? 'bg-[#f5cf4a]' : 'bg-white'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="flex-1 whitespace-pre-wrap">{m.text}</span>
                  {m.from === 'ai' && (
                    <button 
                      onClick={() => playAiAudio(m.text)} 
                      className="shrink-0 p-1 text-[#236b52] hover:bg-[#b9dbcb] border border-[#141414] transition-all" 
                      title="Listen in voice"
                    >
                      <Volume2 className="size-4" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Audio Recording & Text Input Controls */}
        <div className="border-t-2 border-[#141414] p-4 bg-white">
          {listening && (
            <div className="mb-3 flex items-center justify-between bg-[#fff3ef] border-2 border-[#e44f2b] p-3 text-sm font-black text-[#e44f2b]">
              <div className="flex items-center gap-2">
                <span className="size-3 rounded-full bg-[#e44f2b] animate-ping" />
                <span>Recording audio with Whisper… ({recordingSeconds}s / 15s)</span>
              </div>
              <span className="text-xs uppercase bg-[#e44f2b] text-white px-2 py-1">Click Mic to Finish</span>
            </div>
          )}

          <div className="flex gap-2">
            <textarea 
              value={value} 
              onChange={e => setValue(e.target.value)} 
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                  e.preventDefault()
                  onSend()
                }
              }} 
              rows={2} 
              placeholder={tConv('typeOrUseVoice')} 
              className="min-w-0 flex-1 resize-none border-2 border-[#141414] p-3 outline-none font-semibold focus:border-[#236b52]" 
            />
            
            {/* Click to Record / Click to Stop toggle */}
            <button 
              onClick={onVoice} 
              className={`grid size-12 shrink-0 place-items-center self-end border-2 border-[#141414] transition-all shadow-[2px_2px_0_#141414] ${
                listening ? 'bg-[#e44f2b] text-white animate-pulse' : 'bg-white hover:bg-[#b9dbcb]'
              }`} 
              aria-label={tConv('speak')}
              title={listening ? "Click to stop recording" : "Click to speak in your language"}
            >
              {listening ? <MicOff className="size-5" /> : <Mic className="size-5" />}
            </button>

            <button 
              onClick={onSend} 
              className="grid size-12 shrink-0 place-items-center self-end border-2 border-[#141414] bg-[#e44f2b] text-white hover:bg-[#c93f1d] shadow-[2px_2px_0_#141414] transition-all" 
              aria-label={tConv('send')}
            >
              <Send className="size-5" />
            </button>
          </div>

          <div className="mt-4 flex justify-between items-center">
            <button onClick={onBack} className="button-secondary flex items-center gap-1 font-black px-4 py-2 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414]">
              <ArrowLeft className="size-4" /> {tCommon('back')}
            </button>
            <button 
              onClick={onNext} 
              disabled={userMessages === 0} 
              className={`button-primary flex items-center gap-1 font-black px-6 py-2 border-2 border-[#141414] shadow-[3px_3px_0_#141414] transition-all ${
                userMessages === 0 ? 'opacity-50 cursor-not-allowed bg-gray-200' : shouldAdvance ? 'bg-[#236b52] text-white' : 'bg-[#e44f2b] text-white'
              }`}
            >
              {shouldAdvance ? tConv('reviewSummaryReady') : tConv('reviewSummary')} <ArrowRight className="size-4" />
            </button>
          </div>
          {shouldAdvance && (
            <p className="mt-2 text-xs font-semibold text-[#236b52]">{tConv('maximumQuestionsReached')}</p>
          )}
        </div>
      </div>

      <aside className="panel h-fit border-2 border-[#141414] bg-[#f5cf4a] p-5 shadow-[6px_6px_0_#141414]">
        <p className="eyebrow">{tConv('extractedSymptoms')}</p>
        <h3 className="text-2xl font-black">{tConv('whatWeFound')}</h3>
        <div className="mt-4 flex flex-wrap gap-2">
          {symptoms.length === 0 ? (
            <p className="text-sm font-semibold text-[#48453e] bg-white/70 p-3 border border-[#141414] w-full">
              {tConv('noSymptoms')}
            </p>
          ) : (
            symptoms.map(s => (
              <span key={s} className="border-2 border-[#141414] bg-white px-3 py-1 text-xs font-black uppercase shadow-[2px_2px_0_#141414]">
                {s}
              </span>
            ))
          )}
        </div>
      </aside>
    </div>
  )
}

function Summary({
  name, id, data, reports, form, onBack, onNext, playAiAudio, tSum, tCommon, language
}: {
  name: string; id: string; data: any; reports: Report[]; form: Form;
  onBack: () => void; onNext: () => void; playAiAudio: (text: string) => void;
  tSum: any; tCommon: any; language: string
}) {
  const reportsAnalysis = data?.reports_analysis || []
  const allKeyPoints = data?.report_key_points || []
  const allParameters = data?.all_parameters || []

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
        <div className="flex justify-between items-start">
          <div>
            <p className="eyebrow">{tSum('eyebrow')}</p>
            <h2 className="text-3xl font-black">{tSum('title')}</h2>
          </div>
          <span className="text-xs bg-[#236b52] text-white px-3 py-1 border-2 border-[#141414] font-black uppercase">
            Clinician Handoff (English)
          </span>
        </div>

        {/* Patient Details */}
        <div className="mt-6 border-2 border-[#141414] bg-[#f5f1e8] p-4">
          <p className="label font-black text-sm uppercase text-[#8f8b83]">{tSum('patientDetails')}</p>
          <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('name')}:</span><span className="font-black">{form.name}</span></div>
            <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('ageYears')}:</span><span className="font-black">{form.age} years</span></div>
            <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('sex')}:</span><span className="font-black">{form.sex}</span></div>
            <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('phone')}:</span><span className="font-black">{form.phone}</span></div>
            <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('patientId')}:</span><span className="font-black">{id}</span></div>
            {form.bp && <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('bp')}:</span><span className="font-black">{form.bp}</span></div>}
            {form.sugar && <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('bloodSugar')}:</span><span className="font-black">{form.sugar} mg/dL</span></div>}
            {form.temperature && <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('temperature')}:</span><span className="font-black">{form.temperature}°C</span></div>}
            {form.weight && <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('weight')}:</span><span className="font-black">{form.weight} kg</span></div>}
            {form.height && <div className="flex justify-between border-b pb-1 border-[#141414]/20"><span className="font-semibold">{tSum('height')}:</span><span className="font-black">{form.height} cm</span></div>}
          </div>
        </div>

        {/* Requirement 4: Reports Section with AI Important Points listed below each report */}
        <div className="mt-6 border-2 border-[#141414] bg-white p-5 shadow-[4px_4px_0_#141414]">
          <div className="flex items-center justify-between">
            <p className="font-black text-lg flex items-center gap-2">
              <FileText className="size-5 text-[#236b52]" /> {tSum('reports')} & AI Extraction
            </p>
            <span className="text-xs font-bold text-[#8f8b83]">PDF / Image Analysis</span>
          </div>

          <div className="mt-3 space-y-4">
            {reports.length === 0 ? (
              <p className="text-sm font-semibold text-[#8f8b83] bg-[#f5f1e8] p-3 border border-[#141414]">{tSum('none')}</p>
            ) : (
              reports.map((r, idx) => {
                // Find matching analysis or fallback to report key_points or combined
                const matchingAnalysis = reportsAnalysis.find((a: any) => a.filename === r.name)
                const points = matchingAnalysis?.key_points || r.key_points || allKeyPoints

                return (
                  <div key={r.id || idx} className="border-2 border-[#141414] bg-[#faf8f5] p-4">
                    {/* Report header */}
                    <div className="flex items-center justify-between border-b-2 border-[#141414] pb-2">
                      <div className="flex items-center gap-2">
                        <FileText className="size-5 text-[#236b52]" />
                        <span className="font-black text-sm">{r.name}</span>
                        <span className="text-xs text-[#8f8b83]">({r.size})</span>
                      </div>
                      <span className="text-xs font-bold bg-[#b9dbcb] px-2 py-0.5 border border-[#141414]">
                        Analyzed with AI
                      </span>
                    </div>

                    {/* Important Points listed below report column */}
                    <div className="mt-3 bg-white p-3 border-2 border-[#141414]">
                      <p className="text-xs font-black uppercase text-[#236b52] flex items-center gap-1 mb-2">
                        <Sparkles className="size-3.5" /> Important Points Extracted from Report (English):
                      </p>
                      {points && Array.isArray(points) && points.length > 0 ? (
                        <ul className="list-disc list-inside space-y-1 text-sm font-semibold text-[#141414]">
                          {points.map((pt: string, pIdx: number) => (
                            <li key={pIdx} className="leading-snug">{pt}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs font-semibold text-[#8f8b83]">
                          Extracting findings or normal clinical parameters reported.
                        </p>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Parameter Analysis with Color Coding (Phase 2) */}
        {allParameters && allParameters.length > 0 && (
          <div className="mt-6 border-2 border-[#141414] bg-white p-5 shadow-[4px_4px_0_#141414]">
            <div className="flex items-center justify-between border-b-2 border-[#141414] pb-3">
              <p className="font-black text-lg flex items-center gap-2">
                <Activity className="size-5 text-[#e44f2b]" /> Parameter Analysis
              </p>
              <div className="flex gap-2 text-xs font-bold">
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#e44f2b]"></span> Severe</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#f57c00]"></span> Slight</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 bg-[#236b52]"></span> Normal</span>
              </div>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {allParameters.map((param: any, idx: number) => (
                <ParameterCard
                  key={idx}
                  name={param.name}
                  value={param.value}
                  status={param.status}
                  normal_range={param.normal_range}
                  impact={param.impact}
                  suggestion={param.suggestion}
                />
              ))}
            </div>
          </div>
        )}

        {/* AI Analysis & Summary Section - ALWAYS IN ENGLISH (Requirement 4) */}
        <div className="mt-6 border-2 border-[#141414] bg-[#f5f1e8] p-5 shadow-[4px_4px_0_#141414]">
          <div className="flex items-center justify-between border-b-2 border-[#141414] pb-3">
            <p className="font-black text-lg">{tSum('aiAnalysis')}</p>
            <span className="text-xs bg-[#e44f2b] text-white px-2 py-0.5 font-bold uppercase">
              Physician Summary (English)
            </span>
          </div>

          {data?.summary ? (
            typeof data.summary === 'string' ? (
              <p className="mt-4 font-semibold leading-relaxed whitespace-pre-wrap">{data.summary}</p>
            ) : (
              <div className="mt-4 space-y-4">
                {data.summary.chief_complaint && (
                  <div className="border-l-4 border-[#e44f2b] pl-3 bg-white p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#8f8b83]">{tSum('chiefComplaint')}</p>
                    <p className="mt-1 font-bold text-base text-[#141414]">{data.summary.chief_complaint}</p>
                  </div>
                )}

                {data.summary.timeline && (
                  <div className="border-l-4 border-[#236b52] pl-3 bg-white p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#8f8b83]">{tSum('timeline')}</p>
                    <p className="mt-1 font-semibold">{data.summary.timeline}</p>
                  </div>
                )}

                {data.summary.report_findings && (
                  <div className="border-l-4 border-[#f5cf4a] pl-3 bg-white p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#8f8b83]">{tSum('reportFindings')}</p>
                    <div className="mt-2 grid gap-1 text-sm font-semibold">
                      {data.summary.report_findings.pain_nature && (
                        <div><span className="text-[#8f8b83]">{tSum('painNature')}:</span> {data.summary.report_findings.pain_nature}</div>
                      )}
                      {data.summary.report_findings.pain_triggers && (
                        <div><span className="text-[#8f8b83]">{tSum('painTriggers')}:</span> {data.summary.report_findings.pain_triggers}</div>
                      )}
                      {data.summary.report_findings.associated_symptoms && (
                        <div><span className="text-[#8f8b83]">{tSum('associatedSymptoms')}:</span> {data.summary.report_findings.associated_symptoms}</div>
                      )}
                    </div>
                  </div>
                )}

                {data.summary.red_flags && Array.isArray(data.summary.red_flags) && data.summary.red_flags.length > 0 && (
                  <div className="border-l-4 border-[#e44f2b] pl-3 bg-[#fff3ef] p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#e44f2b] flex items-center gap-1">
                      <AlertCircle className="size-4" /> {tSum('redFlags')}
                    </p>
                    <ul className="mt-2 list-disc list-inside space-y-1">
                      {data.summary.red_flags.map((flag: string, idx: number) => (
                        <li key={idx} className="text-sm font-bold text-[#e44f2b]">{flag}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.summary.missing_information && Array.isArray(data.summary.missing_information) && data.summary.missing_information.length > 0 && (
                  <div className="border-l-4 border-[#8f8b83] pl-3 bg-white p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#8f8b83]">{tSum('missingInformation')}</p>
                    <ul className="mt-2 list-disc list-inside space-y-1">
                      {data.summary.missing_information.map((info: string, idx: number) => (
                        <li key={idx} className="text-sm font-semibold">{info}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {data.summary.recommended_specialty && (
                  <div className="border-l-4 border-[#236b52] pl-3 bg-[#b9dbcb] p-3 border-2 border-l-4 border-[#141414]">
                    <p className="text-xs font-black uppercase text-[#236b52]">{tSum('recommendedSpecialty')}</p>
                    <p className="mt-1 text-lg font-black">{data.summary.recommended_specialty}</p>
                  </div>
                )}
              </div>
            )
          ) : (
            <p className="mt-2 font-semibold text-[#8f8b83]">{tSum('aiSummaryWillAppear')}</p>
          )}
        </div>

        {/* Patient-Friendly Summary in Patient's Language (Phase 3) */}
        {data?.patient_summary && (
          <div className="mt-6 border-2 border-[#b9dbcb] bg-[#e8f5e9] p-5 shadow-[4px_4px_0_#141414]">
            <div className="flex items-center justify-between border-b-2 border-[#141414] pb-3">
              <p className="font-black text-lg flex items-center gap-2">
                <Sparkles className="size-5 text-[#236b52]" /> Patient Summary ({language})
              </p>
              <span className="text-xs bg-[#236b52] text-white px-2 py-0.5 font-bold uppercase">
                Your Language
              </span>
            </div>
            <div className="mt-4 font-semibold leading-relaxed whitespace-pre-wrap text-[#141414]">
              {typeof data.patient_summary === 'string' ? data.patient_summary : JSON.stringify(data.patient_summary, null, 2)}
            </div>
          </div>
        )}

        {/* Risk Assessment */}
        <div className="mt-6 border-2 border-[#141414] bg-[#fff3ef] p-4 flex items-center justify-between shadow-[4px_4px_0_#141414]">
          <div>
            <p className="text-xs font-black uppercase text-[#e44f2b]">{tSum('potentialRisk')}</p>
            <p className="text-2xl font-black uppercase">{data?.risk || 'Medium'}</p>
            <p className="text-xs font-semibold text-[#8f8b83]">{tSum('forClinicianReview')}</p>
          </div>
          <span className="text-4xl">⚠️</span>
        </div>

        <button 
          onClick={onNext} 
          className="mt-8 action w-full bg-[#e44f2b] text-white flex items-center justify-center gap-2 font-black py-4 px-6 border-2 border-[#141414] shadow-[4px_4px_0_#141414] hover:shadow-none hover:translate-x-1 hover:translate-y-1 transition-all"
        >
          {tSum('generateToken')} <ArrowRight className="size-5" />
        </button>
        <button 
          onClick={onBack} 
          className="button-secondary mt-3 flex items-center gap-1 font-black px-4 py-2 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414]"
        >
          <ArrowLeft className="size-4" /> {tSum('backToConversation')}
        </button>
      </div>

      <aside className="panel bg-[#b9dbcb] border-2 border-[#141414] p-5 shadow-[6px_6px_0_#141414] h-fit">
        <p className="eyebrow">Triaging Summary</p>
        <p className="text-lg font-black leading-tight mt-2">
          Symptoms, clinical vitals, patient answers, and extracted report points are combined for safe handoff.
        </p>
        <div className="mt-6 p-4 bg-white border-2 border-[#141414] text-xs font-semibold space-y-2">
          <p className="font-black uppercase text-[#236b52]">✓ Standardized Medical Output</p>
          <p>Even if the patient spoke Marwadi or Hindi, all triage issues and lab findings are provided in professional English for hospital doctors.</p>
        </div>
      </aside>
    </div>
  )
}

function Token({ 
  token, id, queue, name, onBack, onDone, tToken, tCommon 
}: { 
  token: string; id: string; queue: { people_ahead: number; estimated_minutes: number; priority: string }; 
  name: string; onBack: () => void; onDone: () => void; tToken: any; tCommon: any 
}) {
  const payload = JSON.stringify({ patient_id: id, token, name })
  const priorityColor = queue.priority === 'high' ? 'bg-[#e44f2b]' : queue.priority === 'low' ? 'bg-[#236b52]' : 'bg-[#f5cf4a]'

  return (
    <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
      <p className="eyebrow">{tToken('eyebrow')}</p>
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <h2 className="text-4xl font-black">{tToken('title')}</h2>
          <p className="mt-2 font-semibold text-[#48453e]">{tToken('description')}</p>
        </div>
        <div className={`border-2 border-[#141414] ${priorityColor} p-4 text-center ${queue.priority === 'medium' ? 'text-black' : 'text-white'} shadow-[4px_4px_0_#141414]`}>
          <p className="text-5xl font-black">{token}</p>
          <b className="uppercase tracking-wider">{queue.priority} {tToken('priority')}</b>
        </div>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        <div className="metric bg-[#f5cf4a] border-2 border-[#141414] p-4 shadow-[3px_3px_0_#141414]">
          <span className="text-xs font-black uppercase text-[#48453e]">{tToken('peopleAhead')}</span>
          <b className="block text-3xl font-black">{queue.people_ahead}</b>
        </div>
        <div className="metric bg-[#b9dbcb] border-2 border-[#141414] p-4 shadow-[3px_3px_0_#141414]">
          <span className="text-xs font-black uppercase text-[#48453e]">{tToken('expectedTime')}</span>
          <b className="block text-3xl font-black">{queue.estimated_minutes} {tToken('min')}</b>
        </div>
        <div className="metric bg-white border-2 border-[#141414] p-4 shadow-[3px_3px_0_#141414]">
          <span className="text-xs font-black uppercase text-[#48453e]">Patient ID</span>
          <b className="block text-xl font-black truncate">{id}</b>
        </div>
      </div>

      <div className="mt-7 flex flex-wrap items-center gap-8 border-2 border-[#141414] p-5 bg-[#f5f1e8]">
        <div className="p-2 bg-white border-2 border-[#141414]">
          <QRCodeSVG value={payload} size={132} level="M" />
        </div>
        <div>
          <p className="label font-black text-xs uppercase text-[#8f8b83]">{tToken('patientToken')}</p>
          <p className="text-2xl font-black">{name}</p>
          <p className="mt-2 text-sm font-semibold text-[#48453e]">{tToken('scanDescription')}</p>
        </div>
      </div>

      <div className="mt-7 flex gap-3">
        <button onClick={onBack} className="button-secondary font-black px-4 py-3 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414]">
          <ArrowLeft className="mr-1 inline size-4" /> {tCommon('back')}
        </button>
        <button onClick={onDone} className="button-primary flex-1 font-black py-3 border-2 border-[#141414] bg-[#141414] text-white shadow-[3px_3px_0_#e44f2b] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all">
          {tToken('openDashboard')} <ArrowRight className="ml-1 inline size-4" />
        </button>
      </div>
    </div>
  )
}

function Returning({ 
  lookup, setLookup, onBack, onOpen, tRet, tCommon 
}: { 
  lookup: string; setLookup: (x: string) => void; onBack: () => void; onOpen: () => void; 
  tRet: any; tCommon: any 
}) {
  return (
    <section className="mx-auto max-w-[720px] px-5 pb-20 pt-20">
      <div className="panel border-2 border-[#141414] bg-white p-8 shadow-[8px_8px_0_#141414]">
        <p className="eyebrow">{tRet('eyebrow')}</p>
        <h1 className="display text-4xl sm:text-6xl font-black">{tRet('title')}</h1>
        <p className="mt-5 font-semibold text-[#48453e]">{tRet('description')}</p>
        <input 
          value={lookup} 
          onChange={e => setLookup(e.target.value)} 
          placeholder="SYN-…" 
          className="mt-8 w-full border-2 border-[#141414] bg-white px-4 py-4 text-xl font-black outline-none focus:border-[#236b52]" 
        />
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button onClick={onOpen} className="action bg-[#141414] text-white flex items-center justify-center gap-2 font-black py-4 border-2 border-[#141414] shadow-[4px_4px_0_#e44f2b]">
            {tRet('openDashboard')} <ArrowRight className="size-5" />
          </button>
          <button onClick={onBack} className="button-secondary flex items-center justify-center gap-2 font-black py-4 border-2 border-[#141414] bg-white shadow-[4px_4px_0_#141414]">
            <ArrowLeft className="size-5" /> {tCommon('back')}
          </button>
        </div>
      </div>
    </section>
  )
}

function Dashboard({ patientId, onNew, onLogout, tDash }: { patientId: string; onNew: () => void; onLogout: () => void; tDash: any }) {
  const [section, setSection] = useState<DashboardSection>('overview')
  const [data, setData] = useState<any>({})
  const [reports, setReports] = useState<any[]>([])
  const [showComparison, setShowComparison] = useState(false)
  const [comparisonData, setComparisonData] = useState<any>(null)
  const [pastReportId, setPastReportId] = useState<number | null>(null)
  const [presentReportId, setPresentReportId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${API}/patients/${patientId}`).then(r => r.json()).then(setData).catch(() => {})
    fetch(`${API}/patients/${patientId}/reports`).then(r => r.json()).then(setReports).catch(() => {})
    fetch(`${API}/patients/${patientId}/visits`).then(r => r.json()).then(v => setData(d => ({ ...d, visits: v }))).catch(() => {})
    fetch(`${API}/patients/${patientId}/prescriptions`).then(r => r.json()).then(p => setData(d => ({ ...d, prescriptions: p }))).catch(() => {})
  }, [patientId])

  const handleCompare = () => {
    if (!pastReportId || !presentReportId || pastReportId === presentReportId) return
    setComparisonLoading(true)
    fetch(`${API}/patients/${patientId}/reports/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId, past_report_id: pastReportId, present_report_id: presentReportId, language: 'English' })
    }).then(r => r.json()).then(setComparisonData).catch(() => alert('Comparison failed')).finally(() => setComparisonLoading(false))
  }

  const deleteReport = (id: number) => confirm('Delete report?') && fetch(`${API}/patients/${patientId}/reports/${id}`, { method: 'DELETE' }).then(() => setReports(r => r.filter(x => x.id !== id)))

  const sections = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'records', label: 'Patient Records', icon: ScanFace },
    { id: 'reports', label: 'Lab Reports', icon: FileText },
    { id: 'prescriptions', label: 'Prescriptions', icon: FileText },
    { id: 'visits', label: 'Visit History', icon: FileText }
  ]

  return (
    <main className="min-h-screen bg-[#f5f1e8] flex">
      <aside className="w-64 bg-white border-r-2 border-[#141414] p-6 hidden lg:block">
        <b className="text-xl font-black">synapse <span className="text-[#e44f2b]">ai</span></b>
        <nav className="mt-8 space-y-2">
          {sections.map(s => (
            <button key={s.id} onClick={() => setSection(s.id as DashboardSection)} className={`w-full flex items-center gap-3 px-4 py-3 font-black border-2 transition-all ${section === s.id ? 'bg-[#e44f2b] text-white border-[#141414]' : 'bg-white border-transparent hover:border-[#141414]'}`}>
              <s.icon className="size-4" /> {s.label}
            </button>
          ))}
        </nav>
        <button onClick={onLogout} className="mt-8 w-full flex items-center gap-2 px-4 py-3 font-black border-2 border-[#141414] bg-white hover:bg-[#f5f1e8] transition-all">
          <LogOut className="size-4" /> Logout
        </button>
      </aside>

      <div className="flex-1">
        <header className="flex items-center justify-between px-5 py-5 lg:px-10 border-b-2 border-[#141414] bg-white lg:hidden">
          <b className="text-xl font-black">synapse <span className="text-[#e44f2b]">ai</span></b>
          <button onClick={onLogout} className="button-secondary flex items-center gap-2 font-black px-4 py-2 border-2 border-[#141414] bg-white shadow-[2px_2px_0_#141414]">
            <LogOut className="size-4" /> Logout
          </button>
        </header>

        <section className="mx-auto max-w-[1180px] px-5 pb-16 pt-8">
          <p className="eyebrow">{tDash('eyebrow')}</p>
          <h1 className="display text-4xl sm:text-5xl font-black">{tDash('title')}</h1>

          {section === 'overview' && (
            <div className="mt-8 space-y-6">
              <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
                <div className="flex items-center justify-between border-b-2 border-[#141414] pb-4 mb-4">
                  <div>
                    <p className="label font-black text-xs uppercase text-[#8f8b83]">{tDash('patientId')}</p>
                    <p className="text-2xl font-black">{patientId}</p>
                  </div>
                  {data.name && <div className="text-right"><p className="text-sm font-black text-[#8f8b83]">Patient Name</p><p className="text-xl font-black">{data.name}</p></div>}
                </div>
                {data.assigned_doctor && <div className="mt-4 bg-[#b9dbcb] border-2 border-[#141414] p-4"><p className="text-xs font-black uppercase text-[#236b52]">Assigned Doctor</p><p className="mt-1 font-black text-lg">{data.assigned_doctor.name}</p><p className="text-sm font-semibold text-[#48453e]">{data.assigned_doctor.specialty}</p></div>}
                <button onClick={onNew} className="action mt-6 w-full bg-[#e44f2b] text-white font-black py-4 border-2 border-[#141414] shadow-[4px_4px_0_#141414]">{tDash('planNewVisit')}</button>
              </div>
              {data.latest_visit && <div className="panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]"><p className="eyebrow">Latest Visit</p><p className="mt-2 font-black text-lg">{new Date(data.latest_visit.created_at).toLocaleDateString()}</p><p className="mt-1 font-semibold text-[#48453e]">{data.latest_visit.summary?.chief_complaint || 'No summary available'}</p></div>}
            </div>
          )}

          {section === 'records' && (
            <div className="mt-8 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
              <p className="eyebrow">Patient Records</p>
              <h2 className="text-2xl font-black mt-2">Your Information</h2>
              <div className="mt-6 grid gap-4 text-sm sm:grid-cols-2">
                <div className="border-b pb-2 border-[#141414]/20"><span className="font-semibold">Name:</span><span className="font-black ml-2">{data.name || 'N/A'}</span></div>
                <div className="border-b pb-2 border-[#141414]/20"><span className="font-semibold">Age:</span><span className="font-black ml-2">{data.age || 'N/A'}</span></div>
                <div className="border-b pb-2 border-[#141414]/20"><span className="font-semibold">Sex:</span><span className="font-black ml-2">{data.sex || 'N/A'}</span></div>
                <div className="border-b pb-2 border-[#141414]/20"><span className="font-semibold">Phone:</span><span className="font-black ml-2">{data.phone || 'N/A'}</span></div>
              </div>
              {data.vitals && <div className="mt-6 bg-[#f5f1e8] border-2 border-[#141414] p-4"><p className="text-xs font-black uppercase text-[#8f8b83]">Vitals</p><div className="mt-2 grid gap-2 text-sm font-semibold">{Object.entries(JSON.parse(data.vitals)).map(([k, v]) => <div key={k}><span className="text-[#8f8b83]">{k}:</span> {String(v)}</div>)}</div></div>}
            </div>
          )}

          {section === 'reports' && (
            <div className="mt-8 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
              <div className="flex items-center justify-between border-b-2 border-[#141414] pb-4 mb-4">
                <div><p className="eyebrow">Lab Reports</p><h2 className="text-2xl font-black">Your Medical Reports</h2></div>
                {reports.length >= 2 && <button onClick={() => setShowComparison(true)} className="flex items-center gap-2 bg-[#236b52] text-white px-4 py-2 font-black border-2 border-[#141414] shadow-[3px_3px_0_#141414]"><Activity className="size-4" /> Compare</button>}
              </div>
              {reports.length === 0 ? <div className="bg-[#f5f1e8] border-2 border-[#141414] p-8 text-center"><FileText className="size-12 mx-auto text-[#8f8b83] mb-4" /><p className="font-black text-lg text-[#8f8b83]">No reports</p></div> : <div className="space-y-3">{reports.map(r => <div key={r.id} className="border-2 border-[#141414] bg-[#faf8f5] p-4 flex items-center justify-between"><div className="flex items-center gap-3"><FileText className="size-5 text-[#236b52]" /><div><p className="font-black text-sm">{r.filename}</p><p className="text-xs font-semibold text-[#8f8b83]">{new Date(r.created_at).toLocaleDateString()}</p></div></div><button onClick={() => deleteReport(r.id)} className="text-[#e44f2b] hover:text-black p-2"><X className="size-4" /></button></div>)}</div>}
            </div>
          )}

          {section === 'prescriptions' && (
            <div className="mt-8 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
              <p className="eyebrow">Prescriptions</p>
              <h2 className="text-2xl font-black mt-2">Your Prescriptions</h2>
              {data.prescriptions?.length ? <div className="mt-6 space-y-4">{data.prescriptions.map((p: any, i: number) => <div key={i} className="border-2 border-[#141414] bg-[#faf8f5] p-4"><p className="font-black text-sm">{p.doctor_notes || 'No notes'}</p><div className="mt-2 text-xs font-semibold text-[#8f8b83]">{new Date(p.created_at).toLocaleDateString()}</div></div>)}</div> : <p className="mt-4 font-semibold text-[#8f8b83]">No prescriptions</p>}
            </div>
          )}

          {section === 'visits' && (
            <div className="mt-8 panel border-2 border-[#141414] bg-white p-6 shadow-[6px_6px_0_#141414]">
              <p className="eyebrow">Visit History</p>
              <h2 className="text-2xl font-black mt-2">All Visits</h2>
              {data.visits?.length ? <div className="mt-6 space-y-4">{data.visits.map((v: any, i: number) => <div key={i} className="border-2 border-[#141414] bg-[#faf8f5] p-4"><p className="font-black text-sm">{new Date(v.created_at).toLocaleDateString()}</p><p className="mt-1 font-semibold text-[#48453e]">{JSON.parse(v.summary)?.chief_complaint || 'No summary'}</p></div>)}</div> : <p className="mt-4 font-semibold text-[#8f8b83]">No visits recorded</p>}
            </div>
          )}

          {showComparison && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
              <div className="bg-white border-2 border-[#141414] shadow-[8px_8px_0_#141414] max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                <div className="sticky top-0 bg-white border-b-2 border-[#141414] p-6 flex items-center justify-between">
                  <h3 className="text-2xl font-black">Compare Reports</h3>
                  <button onClick={() => { setShowComparison(false); setComparisonData(null); setPastReportId(null); setPresentReportId(null) }} className="text-[#e44f2b] hover:text-black p-2"><X className="size-6" /></button>
                </div>
                <div className="p-6">
                  {!comparisonData ? (
                    <>
                      <div className="grid gap-6 sm:grid-cols-2">
                        <div><label className="block text-sm font-black mb-2">Past Report</label><select value={pastReportId || ''} onChange={e => setPastReportId(e.target.value ? parseInt(e.target.value) : null)} className="w-full border-2 border-[#141414] bg-white px-4 py-3 font-black outline-none focus:border-[#236b52]"><option value="">Select past report</option>{reports.map(r => <option key={r.id} value={r.id}>{r.filename}</option>)}</select></div>
                        <div><label className="block text-sm font-black mb-2">Present Report</label><select value={presentReportId || ''} onChange={e => setPresentReportId(e.target.value ? parseInt(e.target.value) : null)} className="w-full border-2 border-[#141414] bg-white px-4 py-3 font-black outline-none focus:border-[#236b52]"><option value="">Select present report</option>{reports.map(r => <option key={r.id} value={r.id}>{r.filename}</option>)}</select></div>
                      </div>
                      <button onClick={handleCompare} disabled={!pastReportId || !presentReportId || comparisonLoading} className="mt-6 w-full bg-[#e44f2b] text-white font-black py-4 border-2 border-[#141414] shadow-[4px_4px_0_#141414] disabled:opacity-50">{comparisonLoading ? 'Comparing...' : 'Compare Reports'}</button>
                    </>
                  ) : (
                    <ReportComparison comparison={comparisonData.comparison} summary={comparisonData.summary} pastReportName={reports.find(r => r.id === pastReportId)?.filename || 'Unknown'} presentReportName={reports.find(r => r.id === presentReportId)?.filename || 'Unknown'} />
                  )}
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
