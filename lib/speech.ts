export const WEB_SPEECH_LANG: Record<string, string> = {
  English: 'en-IN',
  en: 'en-IN',
  हिन्दी: 'hi-IN',
  hi: 'hi-IN',
  বাংলা: 'bn-IN',
  bn: 'bn-IN',
  తెలుగు: 'te-IN',
  te: 'te-IN',
  मराठी: 'mr-IN',
  mr: 'mr-IN',
  தமிழ்: 'ta-IN',
  ta: 'ta-IN',
  ગુજરાતી: 'gu-IN',
  gu: 'gu-IN',
  ಕನ್ನಡ: 'kn-IN',
  kn: 'kn-IN',
  മലയാളം: 'ml-IN',
  ml: 'ml-IN',
  ਪੰਜਾਬੀ: 'pa-IN',
  pa: 'pa-IN',
  অসমীয়া: 'as-IN',
  as: 'as-IN',
  ଓଡ଼ିଆ: 'or-IN',
  or: 'or-IN',
  اردو: 'ur-IN',
  ur: 'ur-IN',
  नेपाली: 'ne-NP',
  ne: 'ne-NP',
  मारवाड़ी: 'hi-IN',
  mwr: 'hi-IN',
  मैथिली: 'hi-IN',
  mai: 'hi-IN',
  कोंकणी: 'mr-IN',
  kok: 'mr-IN',
  डोगरी: 'hi-IN',
  doi: 'hi-IN',
  छत्तीसगढ़ी: 'hi-IN',
  ch: 'hi-IN',
  सिन्धी: 'sd-IN',
  sd: 'ur-IN',
  کٲشُر: 'ur-IN',
  ks: 'ur-IN',
  संस्कृतम्: 'hi-IN',
  sa: 'hi-IN',
  संथाली: 'hi-IN',
  sat: 'hi-IN'
}

type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  continuous: boolean
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null
  onerror: (() => void) | null
  onend: (() => void) | null
  start: () => void
  stop: () => void
}

function recognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === 'undefined') return null
  const w = window as Window & {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
  return w.SpeechRecognition || w.webkitSpeechRecognition || null
}

export function browserSpeechSupported() {
  return !!recognitionCtor()
}

export function startBrowserRecognition(
  language: string,
  onText: (text: string) => void,
  onEnd: () => void
) {
  const Ctor = recognitionCtor()
  if (!Ctor) return null
  const recognition = new Ctor()
  recognition.lang = WEB_SPEECH_LANG[language] || 'en-IN'
  recognition.interimResults = false
  recognition.continuous = false
  recognition.onresult = (event) => {
    const transcript = event.results[0]?.[0]?.transcript || ''
    if (transcript) onText(transcript)
  }
  recognition.onerror = onEnd
  recognition.onend = onEnd
  recognition.start()
  return recognition
}

export function speakInBrowser(text: string, language: string, onEnd: () => void) {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    onEnd()
    return
  }
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  utter.lang = WEB_SPEECH_LANG[language] || 'en-IN'
  utter.onend = onEnd
  utter.onerror = onEnd
  window.speechSynthesis.speak(utter)
}
