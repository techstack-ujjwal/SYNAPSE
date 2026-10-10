from datetime import datetime
from pathlib import Path
import json, os, re, sqlite3, io, base64
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal
from dotenv import load_dotenv
from PyPDF2 import PdfReader

# Load environment variables from .env file
load_dotenv()

# In-memory SQLite with shared cache for FastAPI
DB_PATH = ':memory:'
_global_conn = None

# Configuration from environment variables
MAX_QUESTIONS = int(os.getenv('MAX_QUESTIONS', '8'))
ESTIMATED_MINUTES_PER_PERSON = int(os.getenv('ESTIMATED_MINUTES_PER_PERSON', '4'))
BASE_WAIT_TIME = int(os.getenv('BASE_WAIT_TIME', '8'))

app = FastAPI(title='Synapse AI intake API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

class PatientIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    age: int = Field(ge=0, le=120)
    phone: str = Field(pattern=r'^(?:\+91[6-9]\d{9}|[6-9]\d{9})$')
    sex: str = Field(min_length=1)
    vitals: dict = {}

class ConversationIn(BaseModel):
    patient_id: str = ''
    message: str = Field(min_length=1, max_length=4000)
    language: str = 'English'
    history: list[dict] = []

class SummaryIn(BaseModel):
    patient_id: str = ''
    form: dict = {}
    messages: list[dict] = []
    reports: list[dict] = []
    symptoms: list[str] = []
    language: str = 'English'
    report_data: dict = {}

class AudioTranscribeIn(BaseModel):
    audio_data: str  # Base64 encoded audio
    language: str = 'English'

class TextToSpeechIn(BaseModel):
    text: str
    language: str = 'English'
    voice: str = 'nova'  # nova, shimmer, alloy, echo, fable, onyx

class QueueIn(BaseModel):
    patient_id: str
    priority: str = 'medium'

def get_db():
    global _global_conn
    if _global_conn is None:
        _global_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _global_conn.row_factory = sqlite3.Row
        _global_conn.execute('CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY,name TEXT,age INTEGER,phone TEXT,sex TEXT,vitals TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,filename TEXT,content_type TEXT,bytes INTEGER,extracted_text TEXT,key_points TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,visit_date TEXT,summary TEXT,symptoms TEXT,risk TEXT,priority TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,token TEXT,priority TEXT,status TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,role TEXT,text TEXT,created_at TEXT)')
        _global_conn.commit()
    return _global_conn

def save_conversation_message(patient_id: str, role: str, text: str):
    """Save a conversation message to the database for AI memory."""
    if not patient_id:
        return
    c = get_db()
    c.execute('INSERT INTO conversations (patient_id, role, text, created_at) VALUES (?, ?, ?, ?)',
              (patient_id, role, text, datetime.now().isoformat()))
    c.commit()

def get_conversation_history(patient_id: str, limit: int = 20) -> list[dict]:
    """Retrieve conversation history for AI memory."""
    if not patient_id:
        return []
    c = get_db()
    messages = c.execute('SELECT role, text FROM conversations WHERE patient_id = ? ORDER BY created_at DESC LIMIT ?',
                        (patient_id, limit)).fetchall()
    return [{'role': msg['role'], 'text': msg['text']} for msg in reversed(messages)]

# Hardcoded greetings in all 23 supported languages (Requirement 3)
GREETINGS = {
    'English': 'Hello, I am here to help you. How are you feeling today?',
    'en': 'Hello, I am here to help you. How are you feeling today?',
    'हिन्दी': 'नमस्ते, मैं आपकी मदद करने के लिए यहां हूं। आज आप कैसा महसूस कर रहे हैं?',
    'hi': 'नमस्ते, मैं आपकी मदद करने के लिए यहां हूं। आज आप कैसा महसूस कर रहे हैं?',
    'বাংলা': 'নমস্কার, আমি আপনাকে সাহায্য করতে এখানে আছি। আজ আপনি কেমন অনুভব করছেন?',
    'bn': 'নমস্কার, আমি আপনাকে সাহায্য করতে এখানে আছি। আজ আপনি কেমন অনুভব করছেন?',
    'తెలుగు': 'నమస్కారం, నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను. మీరు ఈరోజు ఎలా భావిస్తున్నారు?',
    'te': 'నమస్కారం, నేను మీకు సహాయం చేయడానికి ఇక్కడ ఉన్నాను. మీరు ఈరోజు ఎలా భావిస్తున్నారు?',
    'मराठी': 'नमस्कार, मी तुम्हाला मदत करण्यासाठी इथे आहे. तुम्हाला आज कसे वाटते आहे?',
    'mr': 'नमस्कार, मी तुम्हाला मदत करण्यासाठी इथे आहे. तुम्हाला आज कसे वाटते आहे?',
    'தமிழ்': 'வணக்கம், நான் உங்களுக்கு உதவ இங்கே இருக்கிறேன். நீங்கள் இன்று எப்படி உணர்கிறீர்கள்?',
    'ta': 'வணக்கம், நான் உங்களுக்கு உதவ இங்கே இருக்கிறேன். நீங்கள் இன்று எப்படி உணர்கிறீர்கள்?',
    'ગુજરાતી': 'નમસ્તે, હું તમારી મદદ કરવા અહીં છું. તમે આજે કેવું અનુભવો છો?',
    'gu': 'નમસ્તે, હું તમારી મદદ કરવા અહીં છું. તમે આજે કેવું અનુભવો છો?',
    'ಕನ್ನಡ': 'ನಮಸ್ಕಾರ, ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ. ನೀವು ಇಂದು ಹೇಗೆ ಭಾವಿಸುತ್ತೀರಿ?',
    'kn': 'ನಮಸ್ಕಾರ, ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ಇಲ್ಲಿದ್ದೇನೆ. ನೀವು ಇಂದು ಹೇಗೆ ಭಾವಿಸುತ್ತೀರಿ?',
    'മലയാളം': 'നമസ്കാരം, ഞാൻ നിങ്ങളെ സഹായിക്കാൻ ഇവിടെയുണ്ട്. നിങ്ങൾക്ക് ഇന്ന് എങ്ങനെയുണ്ട്?',
    'ml': 'നമസ്കാരം, ഞാൻ നിങ്ങളെ സഹായിക്കാൻ ഇവിടെയുണ്ട്. നിങ്ങൾക്ക് ഇന്ന് എങ്ങനെയുണ്ട്?',
    'ਪੰਜਾਬੀ': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ ਤੁਹਾਡੀ ਮਦਦ ਲਈ ਇੱਥੇ ਹਾਂ। ਤੁਸੀਂ ਅੱਜ ਕਿਵੇਂ ਮਹਿਸੂਸ ਕਰ ਰਹੇ ਹੋ?',
    'pa': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਮੈਂ ਤੁਹਾਡੀ ਮਦਦ ਲਈ ਇੱਥੇ ਹਾਂ। ਤੁਸੀਂ ਅੱਜ ਕਿਵੇਂ ਮਹਿਸੂਸ ਕਰ ਰਹੇ ਹੋ?',
    'অসমীয়া': 'নমস্কাৰ, মই আপোনাক সহায় কৰিবলৈ ইয়াত আছো। আপুনি আজি কেনে অনুভৱ কৰিছে?',
    'as': 'নমস্কাৰ, মই আপোনাক সহায় কৰিবলৈ ইয়াত আছো। আপুনি আজি কেনে অনুভৱ কৰিছে?',
    'ଓଡ଼ିଆ': 'ନମସ୍କାର, ମୁଁ ଆପଣଙ୍କୁ ସାହାଯ୍ୟ କରିବାକୁ ଏଠାରେ ଅଛି। ଆପଣ ଆଜି କିପରି ଅନୁଭବ କରୁଛନ୍ତି?',
    'or': 'ନମସ୍କାର, ମୁଁ ଆପଣଙ୍କୁ ସାହାଯ୍ୟ କରିବାକୁ ଏଠାରେ ଅଛି। ଆପଣ ଆଜି କିପରି ଅନୁଭବ କରୁଛନ୍ତି?',
    'اردو': 'السلام علیکم، میں آپ کی مدد کے لیے حاضر ہوں۔ آج آپ کیسی طبیعت محسوس کر رہے ہیں؟',
    'ur': 'السلام علیکم، میں آپ کی مدد کے لیے حاضر ہوں۔ آج آپ کیسی طبیعت محسوس کر رہے ہیں؟',
    'संस्कृतम्': 'नमस्ते, अहं भवतां साहाय्यार्थम् अत्र अस्मि। अद्य भवन्तः कथम् अनुभवन्ति?',
    'sa': 'नमस्ते, अहं भवतां साहाय्यार्थम् अत्र अस्मि। अद्य भवन्तः कथम् अनुभवन्ति?',
    'नेपाली': 'नमस्ते, म तपाईंलाई मद्दत गर्न यहाँ छु। तपाईं आज कस्तो महसुस गर्दै हुनुहुन्छ?',
    'ne': 'नमस्ते, म तपाईंलाई मद्दत गर्न यहाँ छु। तपाईं आज कस्तो महसुस गर्दै हुनुहुन्छ?',
    'कोंकणी': 'नमस्कार, हांव तुमच्या मदतीक हांगा आसां। तुका आयज कशें दिसता?',
    'kok': 'नमस्कार, हांव तुमच्या मदतीक हांगा आसां। तुका आयज कशें दिसता?',
    'मैथिली': 'नमस्कार, हम अहाँक सहायता करय लेल एतय छी। अहाँ आजु कोना अनुभव कऽ रहल छी?',
    'mai': 'नमस्कार, हम अहाँक सहायता करय लेल एतय छी। अहाँ आजु कोना अनुभव कऽ रहल छी?',
    'सिन्धी': 'هيلو، مان توهان جي مدد لاءِ هتي آهيان. توهان اڄ ڪيئن محسوس ڪري رهيا آهيو؟',
    'sd': 'هيلو، مان توهان جي مدد لاءِ هتي آهيان. توهان اڄ ڪيئن محسوس ڪري رهيا آهيو؟',
    'डोगरी': 'नमस्ते, मैं तुहाड़ी मदद लेई इत्थे आं। तुस आज केह्-फुल्ल महसूस करदे ओ?',
    'doi': 'नमस्ते, मैं तुहाड़ी मदद लेई इत्थे आं। तुस आज केह्-फुल्ल महसूस करदे ओ?',
    'کٲشُر': 'اسلام علیکم، بؤ چھس تُہنزِ مدد باپتھ یتین۔ توہیہِ چھوا از کیتھکن باسان؟',
    'ks': 'اسلام علیکم، بؤ چھس تُہنزِ مدد باپتھ یتین۔ توہیہِ چھوا از کیتھکن باسان؟',
    'छत्तीसगढ़ी': 'जय जोहार, मैं ह आप मन के मदद करे बर इहां हंव। आज आप मन ल कइसन लागत हे?',
    'ch': 'जय जोहार, मैं ह आप मन के मदद करे बर इहां हंव। आज आप मन ल कइसन लागत हे?',
    'संथाली': 'ᱡᱚᱦᱟᱨ, ᱤᱧ ᱫᱚ ᱟᱢᱟᱜ ᱜᱚᱲᱚ ᱞᱟᱹᱜᱤᱫ ᱱᱚᱸᱰᱮ ᱢᱤᱱᱟᱹᱧᱟ᱾ ᱛᱮᱦᱮᱧ ᱟᱢ ᱪᱮᱫ ᱞᱮᱠᱟ ᱢᱮᱱᱟᱢᱟ?',
    'sat': 'ᱡᱚᱦᱟᱨ, ᱤᱧ ᱫᱚ ᱟᱢᱟᱜ ᱜᱚᱲᱚ ᱞᱟᱹᱜᱤᱫ ᱱᱚᱸᱰᱮ ᱢᱤᱱᱟᱹᱧᱟ᱾ ᱛᱮᱦᱮᱧ ᱟᱢ ᱪᱮᱫ ᱞᱮᱠᱟ ᱢᱮᱱᱟᱢᱟ?',
    'मारवाड़ी': 'राम राम सा! म्हे थारी मदद सारू हाजर हां। आज थारी तबीयत कियां है?',
    'mwr': 'राम राम सा! म्हे थारी मदद सारू हाजर हां। आज थारी तबीयत कियां है?'
}

def get_greeting(language: str) -> str:
    """Get hardcoded greeting in the specified language."""
    clean_lang = language.strip() if language else 'English'
    return GREETINGS.get(clean_lang, GREETINGS.get('English'))

def history_line(msg: dict) -> str:
    role = msg.get('role') or msg.get('from') or 'patient'
    return f"{role}: {msg.get('text', '')}"


def get_followup_question(payload: ConversationIn, patient_context: str = ""):
    """Generate dynamic follow-up question using OpenAI in patient's selected language (token-optimized)."""
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        # Reduced context window from 8 to 5 messages to save tokens
        conversation_text = "\n".join(history_line(msg) for msg in payload.history[-5:])

        # Token-optimized system prompts
        is_marwadi = payload.language in ['मारवाड़ी', 'mwr', 'Marwadi', 'Marwari']

        if is_marwadi:
            system_instruction = (
                "Medical intake assistant. Reply in authentic Marwadi dialect using Devanagari script. "
                "Use honorifics 'सा', natural expressions. Ask ONE follow-up question. "
                "Concise, caring. Never diagnose."
            )
        else:
            system_instruction = (
                f"Medical intake assistant. Reply in {payload.language}. "
                "Natural, caring tone. Ask ONE follow-up question. "
                "Concise. Never diagnose."
            )

        response = client.chat.completions.create(
            model='gpt-4o-mini',  # Using mini for faster, cheaper responses
            temperature=0.7,
            max_tokens=100,  # Limit response length
            messages=[
                {
                    'role': 'system',
                    'content': system_instruction
                },
                {
                    'role': 'user',
                    'content': f"Chat:\n{conversation_text}\n{patient_context}\n\nAsk one follow-up in {payload.language}."
                }
            ]
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI follow-up question error: {e}")
        return None

def extract(text: str):
    terms = ['fever', 'cough', 'pain', 'breathlessness', 'headache', 'vomiting', 'cold', 'fatigue', 'rash', 'diarrhea',
             'बुखार', 'खांसी', 'दर्द', 'सिरदर्द', 'उल्टी', 'थकान', 'ताप', 'दरद', 'माथो दुखै', 'पेट दुखै']
    found = []
    for x in terms:
        if x.lower() in text.lower():
            found.append(x)
    return list(set(found))

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file content using PdfReader."""
    try:
        pdf_file = io.BytesIO(file_content)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

# Language mapping for Whisper Speech-to-Text
WHISPER_LANG_MAP = {
    'English': 'en', 'en': 'en',
    'हिन्दी': 'hi', 'hi': 'hi',
    'বাংলা': 'bn', 'bn': 'bn',
    'తెలుగు': 'te', 'te': 'te',
    'मराठी': 'mr', 'mr': 'mr',
    'தமிழ்': 'ta', 'ta': 'ta',
    'ગુજરાતી': 'gu', 'gu': 'gu',
    'ಕನ್ನಡ': 'kn', 'kn': 'kn',
    'മലയാളം': 'ml', 'ml': 'ml',
    'ਪੰਜਾਬੀ': 'pa', 'pa': 'pa',
    'অসমীয়া': 'as', 'as': 'as',
    'ଓଡ଼ିଆ': 'or', 'or': 'or',
    'اردو': 'ur', 'ur': 'ur',
    'संस्कृतम्': 'sa', 'sa': 'sa',
    'नेपाली': 'ne', 'ne': 'ne',
    'कोंकणी': 'kok', 'kok': 'kok',
    'मैथिली': 'mai', 'mai': 'mai',
    'सिन्धी': 'sd', 'sd': 'sd',
    'डोगरी': 'doi', 'doi': 'doi',
    'کٲشُر': 'ks', 'ks': 'ks',
    'छत्तीसगढ़ी': 'ch', 'ch': 'ch',
    'संथाली': 'sat', 'sat': 'sat',
    'मारवाड़ी': 'hi', 'mwr': 'hi'  # Marwadi uses Devanagari script mapped to Hindi acoustic model
}

def transcribe_audio(audio_data: str, language: str = 'English') -> Optional[str]:
    """Transcribe audio using OpenAI Whisper API with optimized regional context prompts."""
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        # Clean base64 data URI if present
        clean_audio = audio_data
        if ',' in clean_audio:
            clean_audio = clean_audio.split(',')[1]

        audio_bytes = base64.b64decode(clean_audio)
        whisper_lang = WHISPER_LANG_MAP.get(language, 'en')

        # Optimized prompts for maximum accuracy with minimal token usage
        # Medical context + regional dialect cues for better recognition
        if language in ['मारवाड़ी', 'mwr', 'Marwadi']:
            transcription_prompt = "मरीज़ डॉक्टर बातचीत मारवाड़ी। दर्द बुखार खांसी। सा हां।"
        elif language in ['हिन्दी', 'hi']:
            transcription_prompt = "मरीज़ डॉक्टर बातचीत हिंदी। बुखार दर्द खांसी।"
        elif language in ['मराठी', 'mr']:
            transcription_prompt = "रुग्ण डॉक्टर संभाषण मराठी। ताप खोकला दुखी।"
        elif language in ['বাংলা', 'bn']:
            transcription_prompt = "রোগী ডাক্তার কথোপকথন বাংলা। জ্বর ব্যথা কাশি।"
        elif language in ['తెలుగు', 'te']:
            transcription_prompt = "రోగి వైద్యుడు సంభాషణ తెలుగు। జ్వరం నొప్పి దగ్గు।"
        elif language in ['தமிழ்', 'ta']:
            transcription_prompt = "நோயாளி மருத்துவர் உரையாடல் தமிழ்। காய்ச்சல் வலி இருமல்।"
        elif language in ['ગુજરાતી', 'gu']:
            transcription_prompt = "રોગી ડૉક્ટર વાર્તાલાપ ગુજરાતી। તાવ દુખાવો ખાંસ।"
        elif language in ['ಕನ್ನಡ', 'kn']:
            transcription_prompt = "ರೋಗಿ ವೈದ್ಯ ಸಂಭಾಷಣೆ ಕನ್ನಡ। ಜ್ವರ ನೋವು ಕೆಮ್ಮು।"
        elif language in ['മലയാളം', 'ml']:
            transcription_prompt = "രോഗി ഡോക്ടർ സംഭാഷണം മലയാളം। പനി വേദന ചുമല്।"
        elif language in ['ਪੰਜਾਬੀ', 'pa']:
            transcription_prompt = "ਮਰੀਜ਼ ਡਾਕਟਰ ਗੱਲਬਾਤ ਪੰਜਾਬੀ। ਬੁਖਾਰ ਦਰਦ ਖਾਂਸੀ।"
        else:
            transcription_prompt = "Patient doctor conversation symptoms pain fever cough."

        import tempfile
        suffix = '.webm'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            with open(tmp_path, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model='whisper-1',
                    file=audio_file,
                    language=whisper_lang,
                    prompt=transcription_prompt,
                    temperature=0.0  # Lower temperature for more deterministic, accurate results
                )
            return response.text.strip()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return None

def text_to_speech(text: str, language: str = 'English', voice: str = 'nova') -> Optional[str]:
    """Convert text to speech using OpenAI TTS API with optimized voice selection for Indian languages."""
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        # Voice selection optimized for Indian languages
        # nova: Warm, natural female voice (best for Hindi, Marathi, Gujarati)
        # shimmer: Clear, articulate female voice (best for South Indian languages)
        # alloy: Neutral, balanced voice (good fallback)
        # onyx: Deep male voice (for formal contexts)
        voice_map = {
            'हिन्दी': 'nova', 'hi': 'nova',
            'मराठी': 'nova', 'mr': 'nova',
            'ગુજરાતી': 'nova', 'gu': 'nova',
            'ਪੰਜਾਬੀ': 'nova', 'pa': 'nova',
            'বাংলা': 'shimmer', 'bn': 'shimmer',
            'తెలుగు': 'shimmer', 'te': 'shimmer',
            'தமிழ்': 'shimmer', 'ta': 'shimmer',
            'ಕನ್ನಡ': 'shimmer', 'kn': 'shimmer',
            'മലയാളം': 'shimmer', 'ml': 'shimmer',
            'मारवाड़ी': 'nova', 'mwr': 'nova',
        }
        
        selected_voice = voice_map.get(language, 'nova')
        if voice in ['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'onyx', 'nova', 'sage', 'shimmer', 'verse', 'marin', 'cedar']:
            selected_voice = voice

        # Use tts-1 for faster response (HD quality difference is minimal for conversational speech)
        response = client.audio.speech.create(
            model='tts-1',
            voice=selected_voice,
            input=text,
            speed=1.0  # Normal speed for clarity
        )

        # Convert to base64
        audio_bytes = response.content
        return base64.b64encode(audio_bytes).decode('utf-8')
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def analyze_report_for_key_points(report_content: bytes, content_type: str, filename: str, conversation_summary: str = "") -> list[str]:
    """Analyze medical report (PDF or image) using OpenAI to extract key clinical findings in English."""
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return []

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        extracted_text = ""
        is_image = content_type in ['image/jpeg', 'image/png', 'image/webp']

        if content_type == 'application/pdf':
            extracted_text = extract_text_from_pdf(report_content)

        if not extracted_text:
            # Fallback: check if content is readable as text
            try:
                decoded_str = report_content.decode('utf-8', errors='ignore')
                if any(w in decoded_str.lower() for w in ['test', 'result', 'patient', 'hemoglobin', 'report', 'doctor', 'blood', 'finding', 'mg/dl']):
                    extracted_text = decoded_str
            except:
                pass

        # If text is available
        if extracted_text and len(extracted_text.strip()) > 20:
            prompt = f"""You are a senior medical specialist and clinician. Analyze the medical report provided below ({filename}).
Extract all key medical findings, abnormal laboratory values, impressions, diagnoses, vital observations, or clinical alerts.

CRITICAL INSTRUCTIONS:
1. Return ALL bullet points in clear, professional medical ENGLISH ONLY.
2. Return ONLY a valid JSON array of bullet point strings in English.
3. Keep each bullet point concise, informative, and clinically actionable.
Example format:
["Hemoglobin: 9.8 g/dL (Mild microcytic anemia)", "Elevated ESR: 38 mm/hr", "Chest X-Ray: Clear lung fields, no active infiltration", "Normal sinus rhythm on ECG"]

Report Text ({filename}):
{extracted_text[:12000]}

Context from patient intake:
{conversation_summary[:1000]}

Return ONLY the JSON array:"""

            response = client.chat.completions.create(
                model='gpt-4o',
                temperature=0.2,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a clinical document analyzer. Extract key medical findings and abnormal values into clear bullet points in English only. Return ONLY a JSON array.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            raw = response.choices[0].message.content.strip()

        elif is_image:
            # For image reports (JPG, PNG, WebP), analyze using GPT-4o vision
            base64_img = base64.b64encode(report_content).decode('utf-8')
            mime = content_type

            prompt = f"""Analyze this medical report image ({filename}). Extract all clinically important findings, abnormal lab values, impressions, and diagnoses in English.
Return ONLY a valid JSON array of concise bullet point strings in English.
Format: ["Finding 1 in English", "Finding 2 in English"]
Return ONLY the JSON array:"""

            response = client.chat.completions.create(
                model='gpt-4o',
                temperature=0.2,
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a clinical document vision analyzer. Extract key medical findings into concise English bullet points. Return ONLY a JSON array.'
                    },
                    {
                        'role': 'user',
                        'content': [
                            {'type': 'text', 'text': prompt},
                            {'type': 'image_url', 'image_url': {'url': f"data:{mime};base64,{base64_img}"}}
                        ]
                    }
                ]
            )
            raw = response.choices[0].message.content.strip()
        else:
            return ["Uploaded document attached for clinician examination."]

        # Clean JSON markdown fences if present
        cleaned = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        # Try to find JSON array inside text
        match = re.search(r'\[\s*[\s\S]*?\s*\]', cleaned)
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]

        return [cleaned] if cleaned else []
    except Exception as e:
        print(f"Report analysis error for {filename}: {e}")
        return ["Report attached for physician review."]

def calculate_priority(vitals: dict, symptoms: list[str]) -> Literal['low', 'medium', 'high']:
    """Calculate priority based on vitals and symptoms (fallback rule-based)."""
    score = 0
    bp = vitals.get('bp', '')
    if bp:
        try:
            systolic, diastolic = map(int, bp.split('/'))
            if systolic > 180 or systolic < 90 or diastolic > 120 or diastolic < 60:
                score += 2
        except:
            pass

    sugar = vitals.get('sugar', '')
    if sugar:
        try:
            sugar_val = float(sugar)
            if sugar_val > 200 or sugar_val < 70:
                score += 2
        except:
            pass

    temp = vitals.get('temperature', '')
    if temp:
        try:
            temp_val = float(temp)
            if temp_val > 39 or temp_val < 35:
                score += 2
        except:
            pass

    high_risk_symptoms = ['breathlessness', 'chest pain', 'severe pain', 'fainting']
    for symptom in symptoms:
        if any(hr in str(symptom).lower() for hr in high_risk_symptoms):
            score += 2

    moderate_risk_symptoms = ['fever', 'vomiting', 'headache', 'rash']
    for symptom in symptoms:
        if any(mr in str(symptom).lower() for mr in moderate_risk_symptoms):
            score += 1

    if score >= 4:
        return 'high'
    elif score >= 2:
        return 'medium'
    return 'low'

def ai_determine_priority(vitals: dict, symptoms: list[str], conversation_summary: str) -> Literal['low', 'medium', 'high']:
    """Use AI to determine priority based on comprehensive data."""
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return calculate_priority(vitals, symptoms)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        prompt = f"""Analyze this patient's case and determine triage priority.
Return only one word: "low", "medium", or "high".

Vitals: {json.dumps(vitals)}
Symptoms: {', '.join(symptoms)}
Conversation summary: {conversation_summary}

Priority:"""

        response = client.chat.completions.create(
            model='gpt-4o',
            temperature=0.3,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a medical triage assistant. Analyze patient data and return only one word: low, medium, or high.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        )

        priority = response.choices[0].message.content.strip().lower()
        if priority in ['low', 'medium', 'high']:
            return priority
    except Exception as e:
        print(f"AI priority decision error: {e}")

    return calculate_priority(vitals, symptoms)

@app.get('/health')
def health():
    return {'ok': True, 'service': 'synapse-ai'}

@app.get('/config')
def get_config():
    openai_ok = bool(os.getenv('OPENAI_API_KEY'))
    return {
        'max_questions': MAX_QUESTIONS,
        'estimated_minutes_per_person': ESTIMATED_MINUTES_PER_PERSON,
        'base_wait_time': BASE_WAIT_TIME,
        'openai_configured': openai_ok,
        'whisper_enabled': openai_ok,
        'tts_enabled': openai_ok
    }

@app.post('/patients')
def create_patient(p: PatientIn):
    pid = f'SYN-{datetime.now().strftime("%y%m%d%H%M%S%f")[:14]}'
    c = get_db()
    c.execute('INSERT INTO patients VALUES (?,?,?,?,?,?,?)',
              (pid, p.name, p.age, p.phone, p.sex, json.dumps(p.vitals), datetime.now().isoformat()))
    c.commit()
    return {'patient_id': pid}

@app.get('/patients/{patient_id}')
def get_patient(patient_id: str):
    c = get_db()
    patient = c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail='Patient not found')
    return dict(patient)

@app.post('/patients/{patient_id}/reports')
async def upload_report(patient_id: str, report: UploadFile = File(...)):
    if report.content_type not in {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}:
        return {'ok': False, 'error': 'Only PDF, JPG, and PNG reports are supported'}

    content = await report.read()
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if len(content) > max_size:
        return {'ok': False, 'error': 'File size exceeds 5MB limit'}

    # Extract text from PDF if applicable
    extracted_text = ""
    if report.content_type == 'application/pdf':
        extracted_text = extract_text_from_pdf(content)

    # Immediately analyze report for key points
    key_points = analyze_report_for_key_points(content, report.content_type, report.filename)

    c = get_db()
    cur = c.execute(
        'INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
        (patient_id, report.filename, report.content_type, len(content), extracted_text, json.dumps(key_points), datetime.now().isoformat())
    )
    c.commit()

    return {
        'ok': True,
        'report_id': cur.lastrowid,
        'filename': report.filename,
        'extracted_text': extracted_text,
        'key_points': key_points
    }

@app.get('/patients/{patient_id}/reports')
def get_reports(patient_id: str):
    c = get_db()
    reports = c.execute('SELECT * FROM reports WHERE patient_id = ?', (patient_id,)).fetchall()
    result = []
    for r in reports:
        d = dict(r)
        if d.get('key_points'):
            try:
                d['key_points'] = json.loads(d['key_points'])
            except:
                d['key_points'] = []
        result.append(d)
    return result

@app.delete('/patients/{patient_id}/reports/{report_id}')
def delete_report(patient_id: str, report_id: int):
    c = get_db()
    c.execute('DELETE FROM reports WHERE id = ? AND patient_id = ?', (report_id, patient_id))
    c.commit()
    return {'ok': True}

# Supports both GET and POST for maximum client compatibility (Requirement 3)
@app.api_route('/conversation/initial', methods=['GET', 'POST'])
async def initial_question(request: Request, patient_id: Optional[str] = Query(''), language: Optional[str] = Query(None)):
    target_lang = language or 'English'
    # If POST with JSON body, inspect body for parameters
    if request.method == 'POST':
        try:
            body = await request.json()
            if isinstance(body, dict):
                target_lang = body.get('language') or target_lang
                patient_id = body.get('patient_id') or patient_id
        except:
            pass

    greeting = get_greeting(target_lang)
    return {'question': greeting, 'language': target_lang, 'model': 'hardcoded'}

@app.post('/conversation/next')
def next_question(p: ConversationIn):
    text = ' '.join(x.get('text', '') for x in p.history)

    # Save user message to database
    if p.message:
        save_conversation_message(p.patient_id, 'user', p.message)

    # Get patient context
    c = get_db()
    patient = c.execute('SELECT * FROM patients WHERE id = ?', (p.patient_id,)).fetchone()
    patient_context = ""
    if patient:
        patient_dict = dict(patient)
        vitals = json.loads(patient_dict.get('vitals', '{}'))
        patient_context = f"\nPatient Context:\nName: {patient_dict.get('name', 'Unknown')}\nAge: {patient_dict.get('age', 'Unknown')}\nSex: {patient_dict.get('sex', 'Unknown')}\nVitals: {json.dumps(vitals)}"

    # Load conversation history from database
    db_history = get_conversation_history(p.patient_id, limit=20)
    combined_history = db_history + p.history

    combined_payload = ConversationIn(
        patient_id=p.patient_id,
        message=p.message,
        language=p.language,
        history=combined_history
    )

    q = get_followup_question(combined_payload, patient_context)
    if not q:
        fallback_msg = (
            "राम राम सा, थारी बीमारी रा लक्षण और बताओ।" if p.language in ['मारवाड़ी', 'mwr', 'Marwadi']
            else "कृपया अपनी तकलीफ के बारे में और विस्तार से बताएं।" if p.language in ['हिन्दी', 'hi']
            else "Please continue describing what you are feeling."
        )
        return {'question': fallback_msg, 'language': p.language, 'symptoms': extract(text), 'model': 'none'}

    # Save AI response to database
    save_conversation_message(p.patient_id, 'ai', q)

    return {'question': q, 'language': p.language, 'symptoms': extract(text), 'model': 'gpt-4o'}

@app.post('/summary')
def summary(p: SummaryIn):
    """
    Requirement 4: On summary page, all clinical issues/findings MUST BE IN ENGLISH,
    regardless of what language the patient spoke. All PDF/file reports must be analyzed
    with key points extracted in bullet points below the reports.
    """
    conversation_text = "\n".join(history_line(msg) for msg in p.messages[-12:])

    # Get patient context
    c = get_db()
    patient = c.execute('SELECT * FROM patients WHERE id = ?', (p.patient_id,)).fetchone()
    patient_context = ""
    if patient:
        patient_dict = dict(patient)
        vitals = json.loads(patient_dict.get('vitals', '{}'))
        patient_context = f"\nPatient Context:\nName: {patient_dict.get('name', 'Unknown')}\nAge: {patient_dict.get('age', 'Unknown')}\nSex: {patient_dict.get('sex', 'Unknown')}\nVitals: {json.dumps(vitals)}"

    # Retrieve all reports and their key points
    reports_data = c.execute('SELECT * FROM reports WHERE patient_id = ?', (p.patient_id,)).fetchall()
    reports_context = ""
    report_key_points = []
    reports_analysis = []

    if reports_data:
        reports_context = "\n\nAttached Medical Reports:\n"
        for report in reports_data:
            report_dict = dict(report)
            filename = report_dict.get('filename', 'Report')
            content_type = report_dict.get('content_type', '')
            extracted_text = report_dict.get('extracted_text', '')

            reports_context += f"- {filename} ({content_type})\n"

            # Parse existing key points or generate if missing
            pts = []
            if report_dict.get('key_points'):
                try:
                    pts = json.loads(report_dict['key_points'])
                except:
                    pts = []

            if not pts and extracted_text:
                pts = analyze_report_for_key_points(extracted_text.encode('utf-8'), content_type, filename, conversation_text)
                # Persist generated points
                try:
                    c.execute('UPDATE reports SET key_points = ? WHERE id = ?', (json.dumps(pts), report_dict['id']))
                    c.commit()
                except:
                    pass

            if pts:
                report_key_points.extend(pts)
                reports_analysis.append({
                    'filename': filename,
                    'content_type': content_type,
                    'key_points': pts
                })

    # Token-optimized prompt requiring ENGLISH output for clinician handoff
    system_prompt = (
        "Clinical summarizer. ALL OUTPUT IN ENGLISH ONLY. "
        "Translate patient language to clinical English. "
        "Return JSON: chief_complaint, timeline, relevant_vitals, "
        "report_findings, red_flags, missing_information, recommended_specialty, risk."
    )

    # Build concise context
    symptom_summary = ', '.join(p.symptoms[:10]) if p.symptoms else 'None'
    vitals_summary = str(p.form.get('vitals', {}))
    report_summary = f"{len(reports_analysis)} reports attached" if reports_analysis else "No reports"

    user_prompt = (
        f"Symptoms: {symptom_summary}\n"
        f"Vitals: {vitals_summary}\n"
        f"Reports: {report_summary}\n"
        f"Patient: {patient_context[:200]}\n\n"
        f"Generate clinical summary in English."
    )

    key = os.getenv('OPENAI_API_KEY')
    summary_data = {}
    risk = 'medium'
    model = 'review'

    if key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            response = client.chat.completions.create(
                model='gpt-4o-mini',  # Use mini for cost efficiency
                temperature=0.2,
                response_format={'type': 'json_object'},
                max_tokens=500,  # Limit output length
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ]
            )
            result = json.loads(response.choices[0].message.content)
            summary_data = result
            risk = str(result.get('risk', 'medium'))
            model = 'openai'
        except Exception as e:
            print(f"OpenAI summary error: {e}")

    if not summary_data:
        symptom_str = ', '.join(p.symptoms) or 'Reported during intake consultation'
        summary_data = {
            'chief_complaint': f"Reported symptoms: {symptom_str}",
            'timeline': 'Not specified by patient',
            'relevant_vitals': {
                'blood_pressure': p.form.get('vitals', {}).get('bp') or None,
                'blood_sugar': p.form.get('vitals', {}).get('sugar') or None,
                'weight': p.form.get('vitals', {}).get('weight') or None,
                'height': p.form.get('vitals', {}).get('height') or None,
                'temperature': p.form.get('vitals', {}).get('temperature') or None
            },
            'report_findings': {
                'pain_nature': 'Detailed during consultation',
                'pain_triggers': 'None reported',
                'associated_symptoms': symptom_str
            },
            'red_flags': [],
            'missing_information': ['Baseline vitals pending clinical confirmation'],
            'recommended_specialty': 'General Medicine'
        }

    # AI-assisted clinical triage priority
    priority = ai_determine_priority(p.form.get('vitals', {}), p.symptoms, conversation_text)

    # Save visit record
    c.execute('INSERT INTO visits (patient_id, visit_date, summary, symptoms, risk, priority, created_at) VALUES (?,?,?,?,?,?,?)',
              (p.patient_id, datetime.now().isoformat(), json.dumps(summary_data), json.dumps(p.symptoms), risk, priority, datetime.now().isoformat()))
    c.commit()

    return {
        'patient_id': p.patient_id,
        'summary': summary_data,
        'risk': risk,
        'priority': priority,
        'model': model,
        'reports_analysis': reports_analysis,
        'report_key_points': list(dict.fromkeys(report_key_points))  # De-duplicate while preserving order
    }

@app.post('/audio/transcribe')
def transcribe_endpoint(p: AudioTranscribeIn):
    """Transcribe audio using OpenAI Whisper API with high-accuracy dialect tuning."""
    text = transcribe_audio(p.audio_data, p.language)
    if not text:
        return {'error': 'Transcription failed or microphone silent.', 'text': ''}
    return {'text': text, 'language': p.language}

@app.post('/audio/tts')
def tts_endpoint(p: TextToSpeechIn):
    """Convert text to speech using OpenAI TTS API with natural vernacular accent."""
    audio_base64 = text_to_speech(p.text, p.language, p.voice)
    if not audio_base64:
        return {'error': 'TTS generation failed.', 'audio': ''}
    return {'audio': audio_base64, 'language': p.language, 'voice': p.voice}

@app.get('/queue')
def queue(patient_id: Optional[str] = Query(None)):
    c = get_db()
    waiting_count = c.execute("SELECT COUNT(*) FROM queue WHERE status = 'waiting'").fetchone()[0]

    result = {
        'people_ahead': max(0, waiting_count),
        'estimated_minutes': max(0, waiting_count) * ESTIMATED_MINUTES_PER_PERSON + BASE_WAIT_TIME,
        'next_token': waiting_count + 1,
        'prefix': 'S'
    }

    if patient_id:
        queue_entry = c.execute("SELECT * FROM queue WHERE patient_id = ? AND status = 'waiting' ORDER BY created_at DESC LIMIT 1", (patient_id,)).fetchone()
        if queue_entry:
            entry = dict(queue_entry)
            position = c.execute("SELECT COUNT(*) FROM queue WHERE status = 'waiting' AND created_at < ?", (entry['created_at'],)).fetchone()[0]
            result.update({
                'token': entry['token'],
                'position': position + 1,
                'priority': entry['priority'],
                'patient_id': patient_id
            })

    return result

@app.post('/queue')
def add_to_queue(q: QueueIn):
    c = get_db()
    token = f"S-{datetime.now().strftime('%y%m%d%H%M%S')[:10]}-{c.execute('SELECT COUNT(*) FROM queue').fetchone()[0] + 1}"
    valid_priorities = ['low', 'medium', 'high']
    priority = q.priority if q.priority in valid_priorities else 'medium'
    c.execute('INSERT INTO queue (patient_id, token, priority, status, created_at) VALUES (?,?,?,?,?)',
              (q.patient_id, token, priority, 'waiting', datetime.now().isoformat()))
    c.commit()
    return {'token': token, 'priority': priority, 'status': 'waiting'}

@app.patch('/queue/{queue_id}/status')
def update_queue_status(queue_id: int, status: Literal['waiting', 'in_consultation', 'completed']):
    c = get_db()
    c.execute('UPDATE queue SET status = ? WHERE id = ?', (status, queue_id))
    c.commit()
    return {'ok': True}

@app.get('/patients/{patient_id}/visits')
def get_patient_visits(patient_id: str):
    c = get_db()
    visits = c.execute('SELECT * FROM visits WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    return [dict(v) for v in visits]

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
