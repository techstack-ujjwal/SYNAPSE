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
    symptoms: list[str] = []

class DoctorIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    specialty: str = Field(min_length=2, max_length=50)
    phone: str = Field(pattern=r'^(?:\+91[6-9]\d{9}|[6-9]\d{9})$')
    is_active: bool = True

class PrescriptionIn(BaseModel):
    patient_id: str
    visit_id: Optional[int] = None
    doctor_id: str
    doctor_notes: str = ''
    medications: list[dict] = []
    language: str = 'English'

class ReportComparisonIn(BaseModel):
    patient_id: str
    past_report_id: int
    present_report_id: int
    language: str = 'English'

class HandwrittenReportIn(BaseModel):
    patient_id: str
    language: str = 'English'

class GenerateReportIn(BaseModel):
    patient_id: str
    doctor_id: str
    doctor_notes: str = ''
    medications: list[dict] = []
    diagnosis: str = ''
    language: str = 'English'

class ReassignDoctorIn(BaseModel):
    patient_id: str
    new_doctor_id: str

def get_db():
    global _global_conn
    if _global_conn is None:
        _global_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _global_conn.row_factory = sqlite3.Row
        _global_conn.execute('CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY,name TEXT,age INTEGER,phone TEXT,sex TEXT,vitals TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,filename TEXT,content_type TEXT,bytes INTEGER,extracted_text TEXT,key_points TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,visit_date TEXT,summary TEXT,symptoms TEXT,risk TEXT,priority TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,token TEXT,priority TEXT,status TEXT,assigned_doctor_id TEXT,consultation_type TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,role TEXT,text TEXT,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS doctors (id TEXT PRIMARY KEY,name TEXT,specialty TEXT,phone TEXT,is_active INTEGER,created_at TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS prescriptions (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,visit_id INTEGER,doctor_id TEXT,doctor_notes TEXT,medications TEXT,created_at TEXT,language TEXT)')
        _global_conn.execute('CREATE TABLE IF NOT EXISTS report_comparisons (id INTEGER PRIMARY KEY AUTOINCREMENT,patient_id TEXT,past_report_id INTEGER,present_report_id INTEGER,comparison_summary TEXT,created_at TEXT)')
        _global_conn.commit()

        # Seed doctors if table is empty
        doctor_count = _global_conn.execute('SELECT COUNT(*) FROM doctors').fetchone()[0]
        if doctor_count == 0:
            seed_doctors()
    return _global_conn

def seed_doctors():
    """Seed the database with proxy doctors."""
    c = get_db()
    doctors = [
        ('DOC-001', 'Dr. Anus Kumar', 'Cardiology', '+919876543210', 1, datetime.now().isoformat()),
        ('DOC-002', 'Dr. Priya Sharma', 'General Medicine', '+919876543211', 1, datetime.now().isoformat()),
        ('DOC-003', 'Dr. Rajesh Gupta', 'Pediatrics', '+919876543212', 1, datetime.now().isoformat()),
        ('DOC-004', 'Dr. Meena Patel', 'Orthopedics', '+919876543213', 1, datetime.now().isoformat()),
        ('DOC-005', 'Dr. Vikram Singh', 'Dermatology', '+919876543214', 1, datetime.now().isoformat()),
        ('DOC-006', 'Dr. Sunita Verma', 'Gynecology', '+919876543215', 1, datetime.now().isoformat()),
        ('DOC-007', 'Dr. Amit Kumar', 'Neurology', '+919876543216', 1, datetime.now().isoformat()),
        ('DOC-008', 'Dr. Kavita Rao', 'Ophthalmology', '+919876543217', 1, datetime.now().isoformat()),
    ]
    for doctor in doctors:
        c.execute('INSERT INTO doctors (id, name, specialty, phone, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)', doctor)
    c.commit()
    print(f"Seeded {len(doctors)} doctors into database")

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

def analyze_parameter_normality(parameter_name: str, value_str: str, sex: str = 'Male', age: int = 30, language: str = 'English') -> dict:
    """
    Analyze a medical parameter and determine if it's normal, slightly abnormal, or severely abnormal.
    Uses AI to generate impact and suggestions dynamically. Returns dict with status, normal_range, impact, and suggestion.
    """
    param_name_lower = parameter_name.lower()

    # Extract numeric value from string
    import re
    numeric_match = re.search(r'[\d.]+', value_str)
    if not numeric_match:
        return {
            'name': parameter_name,
            'value': value_str,
            'status': 'unknown',
            'normal_range': 'N/A',
            'impact': 'Unable to analyze - non-numeric value',
            'suggestion': 'Please consult doctor for interpretation'
        }

    value = float(numeric_match.group())

    # Define normal ranges based on parameter (rule-based for status determination)
    status = 'unknown'
    normal_range = 'N/A'
    unit = ''

    if 'hemoglobin' in param_name_lower or 'hb' in param_name_lower:
        if sex.lower() == 'female':
            normal_min, normal_max = 11.0, 15.0
        else:
            normal_min, normal_max = 12.0, 17.0

        if value < normal_min * 0.7:
            status = 'severely_low'
        elif value < normal_min:
            status = 'slightly_low'
        elif value > normal_max * 1.2:
            status = 'severely_high'
        elif value > normal_max:
            status = 'slightly_high'
        else:
            status = 'normal'

        normal_range = f'{normal_min}-{normal_max} g/dL'
        unit = 'g/dL'
        value_display = f'{value} g/dL'

    elif 'blood pressure' in param_name_lower or 'bp' in param_name_lower:
        if '/' in value_str:
            parts = value_str.split('/')
            if len(parts) >= 2:
                try:
                    systolic = float(re.search(r'[\d.]+', parts[0]).group())
                    diastolic = float(re.search(r'[\d.]+', parts[1]).group())

                    if systolic > 180 or diastolic > 120:
                        status = 'severely_high'
                    elif systolic > 140 or diastolic > 90:
                        status = 'slightly_high'
                    elif systolic < 90 or diastolic < 60:
                        status = 'severely_low'
                    else:
                        status = 'normal'

                    normal_range = '90-120 / 60-80 mmHg'
                    unit = 'mmHg'
                    value_display = f'{systolic}/{diastolic} mmHg'
                except:
                    return {
                        'name': parameter_name,
                        'value': value_str,
                        'status': 'unknown',
                        'normal_range': '90-120 / 60-80 mmHg',
                        'impact': 'Unable to parse blood pressure values',
                        'suggestion': 'Please ensure format is systolic/diastolic (e.g., 120/80)'
                    }
        else:
            return {
                'name': parameter_name,
                'value': value_str,
                'status': 'unknown',
                'normal_range': '90-120 / 60-80 mmHg',
                'impact': 'Unable to parse blood pressure values',
                'suggestion': 'Please ensure format is systolic/diastolic (e.g., 120/80)'
            }

    elif 'blood sugar' in param_name_lower or 'glucose' in param_name_lower or 'sugar' in param_name_lower:
        normal_min, normal_max = 70.0, 140.0

        if value < 50:
            status = 'severely_low'
        elif value < normal_min:
            status = 'slightly_low'
        elif value > 300:
            status = 'severely_high'
        elif value > normal_max:
            status = 'slightly_high'
        else:
            status = 'normal'

        normal_range = f'{normal_min}-{normal_max} mg/dL (fasting)'
        unit = 'mg/dL'
        value_display = f'{value} mg/dL'

    elif 'wbc' in param_name_lower or 'white blood' in param_name_lower:
        normal_min, normal_max = 4500.0, 11000.0

        if value < 2000:
            status = 'severely_low'
        elif value < normal_min:
            status = 'slightly_low'
        elif value > 20000:
            status = 'severely_high'
        elif value > normal_max:
            status = 'slightly_high'
        else:
            status = 'normal'

        normal_range = f'{int(normal_min)}-{int(normal_max)} cells/μL'
        unit = 'cells/μL'
        value_display = f'{int(value)} cells/μL'

    elif 'platelet' in param_name_lower:
        normal_min, normal_max = 150000.0, 450000.0

        if value < 50000:
            status = 'severely_low'
        elif value < normal_min:
            status = 'slightly_low'
        elif value > 600000:
            status = 'severely_high'
        elif value > normal_max:
            status = 'slightly_high'
        else:
            status = 'normal'

        normal_range = f'{int(normal_min)}-{int(normal_max)}/μL'
        unit = '/μL'
        value_display = f'{int(value)}/μL'

    elif 'cholesterol' in param_name_lower:
        normal_max = 200.0

        if value > 300:
            status = 'severely_high'
        elif value > normal_max:
            status = 'slightly_high'
        else:
            status = 'normal'

        normal_range = f'<{normal_max} mg/dL'
        unit = 'mg/dL'
        value_display = f'{value} mg/dL'

    else:
        return {
            'name': parameter_name,
            'value': value_str,
            'status': 'unknown',
            'normal_range': 'N/A',
            'impact': 'Parameter analysis not available',
            'suggestion': 'Consult doctor for interpretation'
        }

    # Use AI to generate impact and suggestion (NO HARDCODING)
    impact, suggestion = generate_parameter_explanation(
        parameter_name, value_display, status, normal_range, sex, age, language
    )

    return {
        'name': parameter_name,
        'value': value_display,
        'unit': unit,
        'status': status,
        'normal_range': normal_range,
        'impact': impact,
        'suggestion': suggestion
    }

def generate_parameter_explanation(parameter_name: str, value: str, status: str, normal_range: str, sex: str, age: int, language: str) -> tuple[str, str]:
    """
    Use AI to generate impact and suggestion for a medical parameter.
    Returns (impact, suggestion) tuple.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        # Fallback when AI is unavailable
        fallback_impact = f"{parameter_name} is {status.replace('_', ' ')}"
        fallback_suggestion = "Please consult doctor for interpretation"
        return fallback_impact, fallback_suggestion

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        system_prompt = f"""You are a medical assistant. Given a medical parameter, its value, status, and normal range, provide:
1. A brief impact explanation (what this means for the patient's health)
2. A practical suggestion (what the patient should do)

Response format: JSON with keys "impact" and "suggestion".
Keep both responses concise (under 30 words each), clear, and actionable.
If status is "normal", provide reassuring explanation.
If status is "severely_low" or "severely_high", emphasize urgency.
Respond in {language}."""

        user_prompt = f"""Parameter: {parameter_name}
Value: {value}
Status: {status}
Normal Range: {normal_range}
Patient Sex: {sex}
Patient Age: {age}

Generate impact and suggestion."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            response_format={'type': 'json_object'},
            max_tokens=150,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        return result.get('impact', 'Unable to generate impact'), result.get('suggestion', 'Unable to generate suggestion')

    except Exception as e:
        print(f"AI parameter explanation error: {e}")
        return "Analysis unavailable", "Please consult doctor"

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

def translate_medical_summary(text: str, target_language: str = 'English') -> str:
    """
    Translate medical summary to patient's selected language using AI.
    Preserves medical terminology accuracy while making it patient-friendly.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return text  # Return original if AI unavailable

    if target_language.lower() == 'english' or target_language == 'en':
        return text  # No translation needed

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        system_prompt = f"""You are a medical translator. Translate the following medical summary into {target_language}.

CRITICAL RULES:
1. Preserve medical accuracy - do not simplify or alter medical facts
2. Use patient-friendly language while maintaining clinical precision
3. Keep technical medical terms in English if no common translation exists
4. Ensure the translation is natural and culturally appropriate
5. Keep the same structure and formatting as the original
6. Do NOT add or remove information

Return ONLY the translated text, no explanations."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            max_tokens=1000,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text}
            ]
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # Return original on error

def compare_reports(past_report_data: dict, present_report_data: dict, language: str = 'English') -> dict:
    """
    Compare two medical reports and identify improvements, deteriorations, and changes.
    Uses AI to generate intelligent comparison summary.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return {
            'comparison': {
                'improved': [],
                'deteriorated': [],
                'unchanged': [],
                'new_abnormalities': [],
                'resolved_abnormalities': []
            },
            'summary': 'AI comparison unavailable - please consult doctor',
            'notes': 'OpenAI API not configured'
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        # Extract key points from both reports
        past_key_points = past_report_data.get('key_points', [])
        present_key_points = present_report_data.get('key_points', [])

        # If key_points is a dict (new format), extract the array
        if isinstance(past_key_points, dict):
            past_key_points = past_key_points.get('key_points', [])
        if isinstance(present_key_points, dict):
            present_key_points = present_key_points.get('key_points', [])

        past_text = '\n'.join(past_key_points) if past_key_points else 'No data'
        present_text = '\n'.join(present_key_points) if present_key_points else 'No data'

        system_prompt = f"""You are a medical report comparison specialist. Compare two medical reports and identify changes.

CRITICAL RULES:
1. Identify which parameters have improved (moved toward normal range)
2. Identify which parameters have deteriorated (moved away from normal range)
3. Identify which parameters remain unchanged
4. Identify new abnormalities that appeared in the present report
5. Identify abnormalities that have resolved (returned to normal)
6. Return ONLY a valid JSON object with the following structure:
{{
  "improved": ["Parameter X: description of improvement"],
  "deteriorated": ["Parameter Y: description of deterioration"],
  "unchanged": ["Parameter Z: within normal range"],
  "new_abnormalities": ["Parameter A: new concern"],
  "resolved_abnormalities": ["Parameter B: now normal"]
}}
7. Keep each description concise (under 20 words)
8. Provide summary in {language} if possible, otherwise English

Return ONLY the JSON object, no explanations."""

        user_prompt = f"""PAST REPORT ({past_report_data.get('filename', 'Unknown')}):
{past_text}

PRESENT REPORT ({present_report_data.get('filename', 'Unknown')}):
{present_text}

Compare these two reports and identify changes."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            response_format={'type': 'json_object'},
            max_tokens=800,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )

        result = json.loads(response.choices[0].message.content)

        # Generate a summary in patient's language
        summary_prompt = f"""Based on the comparison data: {json.dumps(result)}, provide a brief summary (under 50 words) in {language} explaining the overall trend.
Highlight if the patient's condition has improved, worsened, or remained stable.
If no significant changes, state that clearly."""

        summary_response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            max_tokens=150,
            messages=[
                {'role': 'system', 'content': 'You are a medical summary assistant. Provide brief, clear summaries in the specified language.'},
                {'role': 'user', 'content': summary_prompt}
            ]
        )

        summary_text = summary_response.choices[0].message.content.strip()

        return {
            'comparison': result,
            'summary': summary_text,
            'notes': 'AI-generated comparison'
        }

    except Exception as e:
        print(f"Report comparison error: {e}")
        return {
            'comparison': {
                'improved': [],
                'deteriorated': [],
                'unchanged': [],
                'new_abnormalities': [],
                'resolved_abnormalities': []
            },
            'summary': 'Comparison analysis failed - please consult doctor',
            'notes': f'Error: {str(e)}'
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

def analyze_report_for_key_points(report_content: bytes, content_type: str, filename: str, conversation_summary: str = "", patient_sex: str = 'Male', patient_age: int = 30, language: str = 'English') -> dict:
    """
    Analyze medical report (PDF or image) using OpenAI to extract key clinical findings in English.
    Returns dict with key_points and analyzed_parameters with color-coding status.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return {
            'key_points': ["Report analysis unavailable - API not configured"],
            'parameters': []
        }

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
            return {
                'key_points': ["Uploaded document attached for clinician examination."],
                'parameters': []
            }

        # Clean JSON markdown fences if present
        cleaned = re.sub(r'^```json\s*', '', raw, flags=re.IGNORECASE)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned).strip()

        # Try to find JSON array inside text
        match = re.search(r'\[\s*[\s\S]*?\s*\]', cleaned)
        key_points = []
        if match:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, list):
                key_points = [str(item).strip() for item in parsed if item]
        elif cleaned:
            key_points = [cleaned]

        # Analyze parameters for color-coding
        parameters = []
        for point in key_points:
            # Try to extract parameter name and value
            # Pattern: "Parameter: value unit" or "Parameter value unit"
            param_match = re.match(r'^([A-Za-z\s]+?):?\s*([\d./]+\s*[a-zA-Z/]*|\d+)', point)
            if param_match:
                param_name = param_match.group(1).strip()
                param_value = param_match.group(2).strip()

                # Analyze this parameter with AI-generated explanations
                analysis = analyze_parameter_normality(param_name, param_value, patient_sex, patient_age, language)
                parameters.append(analysis)

        return {
            'key_points': key_points,
            'parameters': parameters
        }
    except Exception as e:
        print(f"Report analysis error for {filename}: {e}")
        return {
            'key_points': ["Report attached for physician review."],
            'parameters': []
        }

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

def match_doctor_specialty(symptoms: list[str], conversation_summary: str = "") -> str:
    """
    Phase 11.2: Match patient symptoms to appropriate doctor specialty.
    Returns doctor_id of the most appropriate specialist.
    """
    # Specialty mapping based on symptoms
    specialty_keywords = {
        'Cardiology': ['chest pain', 'heart', 'cardiac', 'palpitation', 'breathlessness', 'shortness of breath', 'hypertension', 'bp', 'blood pressure'],
        'Pediatrics': ['child', 'kid', 'baby', 'infant', 'toddler', 'children', 'pediatric'],
        'Orthopedics': ['bone', 'joint', 'fracture', 'sprain', 'muscle', 'back pain', 'knee', 'shoulder', 'arthritis'],
        'Dermatology': ['skin', 'rash', 'itch', 'acne', 'eczema', 'dermatitis', 'fungal', 'allergy'],
        'Ophthalmology': ['eye', 'vision', 'blurry', 'cataract', 'glaucoma', 'conjunctivitis', 'sight'],
        'Neurology': ['headache', 'migraine', 'seizure', 'dizziness', 'numbness', 'tingling', 'stroke', 'memory', 'neural'],
        'Gynecology': ['pregnant', 'pregnancy', 'menstrual', 'period', 'uterine', 'ovarian', 'women', 'female', 'abortion'],
    }

    # Combine symptoms and conversation summary for analysis
    all_text = ' '.join(symptoms) + ' ' + conversation_summary.lower()

    # Score each specialty based on keyword matches
    specialty_scores = {}
    for specialty, keywords in specialty_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in all_text:
                score += 1
        specialty_scores[specialty] = score

    # Find the specialty with highest score
    best_specialty = max(specialty_scores, key=specialty_scores.get) if specialty_scores else 'General Medicine'

    # If no matches or low score, default to General Medicine
    if specialty_scores[best_specialty] == 0:
        best_specialty = 'General Medicine'

    # Get doctor ID for the best specialty
    c = get_db()
    # Get an active doctor with the matching specialty
    doctor = c.execute(
        'SELECT id FROM doctors WHERE specialty = ? AND is_active = 1 LIMIT 1',
        (best_specialty,)
    ).fetchone()

    if doctor:
        return doctor[0]

    # Fallback: return first active General Medicine doctor
    doctor = c.execute(
        'SELECT id FROM doctors WHERE specialty = ? AND is_active = 1 LIMIT 1',
        ('General Medicine',)
    ).fetchone()

    if doctor:
        return doctor[0]

    # Ultimate fallback: return first active doctor
    doctor = c.execute('SELECT id FROM doctors WHERE is_active = 1 LIMIT 1').fetchone()
    return doctor[0] if doctor else 'DOC-002'

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

    patient_dict = dict(patient)

    # Get latest visit
    latest_visit = c.execute('SELECT * FROM visits WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1', (patient_id,)).fetchone()
    if latest_visit:
        visit_dict = dict(latest_visit)
        if visit_dict.get('summary'):
            try:
                visit_dict['summary'] = json.loads(visit_dict['summary'])
            except:
                pass
        patient_dict['latest_visit'] = visit_dict

    # Get assigned doctor from queue
    queue_entry = c.execute("SELECT * FROM queue WHERE patient_id = ? AND status IN ('waiting', 'in_consultation') ORDER BY created_at DESC LIMIT 1", (patient_id,)).fetchone()
    if queue_entry:
        queue_dict = dict(queue_entry)
        if queue_dict.get('assigned_doctor_id'):
            doctor = c.execute('SELECT * FROM doctors WHERE id = ?', (queue_dict['assigned_doctor_id'],)).fetchone()
            if doctor:
                patient_dict['assigned_doctor'] = dict(doctor)

    # Get recent prescriptions
    prescriptions = c.execute('SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC LIMIT 5', (patient_id,)).fetchall()
    prescriptions_list = []
    for p in prescriptions:
        p_dict = dict(p)
        if p_dict.get('medications'):
            try:
                p_dict['medications'] = json.loads(p_dict['medications'])
            except:
                p_dict['medications'] = []
        prescriptions_list.append(p_dict)
    patient_dict['recent_prescriptions'] = prescriptions_list

    return patient_dict

@app.post('/patients/{patient_id}/reports')
async def upload_report(patient_id: str, report: UploadFile = File(...)):
    if report.content_type not in {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}:
        return {'ok': False, 'error': 'Only PDF, JPG, and PNG reports are supported'}

    content = await report.read()
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if len(content) > max_size:
        return {'ok': False, 'error': 'File size exceeds 5MB limit'}

    # Get patient info for parameter analysis
    c = get_db()
    patient = c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
    patient_sex = 'Male'
    patient_age = 30
    patient_language = 'English'
    if patient:
        patient_dict = dict(patient)
        patient_sex = patient_dict.get('sex', 'Male')
        patient_age = patient_dict.get('age', 30)
        # Language could be stored in patient record or determined from session
        # For now, default to English - will be enhanced in Phase 3

    # Extract text from PDF if applicable
    extracted_text = ""
    if report.content_type == 'application/pdf':
        extracted_text = extract_text_from_pdf(content)

    # Immediately analyze report for key points with parameter analysis
    analysis_result = analyze_report_for_key_points(content, report.content_type, report.filename, "", patient_sex, patient_age, patient_language)
    key_points = analysis_result.get('key_points', [])
    parameters = analysis_result.get('parameters', [])

    cur = c.execute(
        'INSERT INTO reports (patient_id, filename, content_type, bytes, extracted_text, key_points, created_at) VALUES (?,?,?,?,?,?,?)',
        (patient_id, report.filename, report.content_type, len(content), extracted_text, json.dumps(analysis_result), datetime.now().isoformat())
    )
    c.commit()

    return {
        'ok': True,
        'report_id': cur.lastrowid,
        'filename': report.filename,
        'extracted_text': extracted_text,
        'key_points': key_points,
        'parameters': parameters
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
                parsed = json.loads(d['key_points'])
                # Handle both old format (list) and new format (dict)
                if isinstance(parsed, dict):
                    d['key_points'] = parsed.get('key_points', [])
                    d['parameters'] = parsed.get('parameters', [])
                else:
                    d['key_points'] = parsed
                    d['parameters'] = []
            except:
                d['key_points'] = []
                d['parameters'] = []
        else:
            d['key_points'] = []
            d['parameters'] = []
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
            analysis_result = {}
            if report_dict.get('key_points'):
                try:
                    analysis_result = json.loads(report_dict['key_points'])
                except:
                    analysis_result = {}

            # Handle both old format (list) and new format (dict with key_points and parameters)
            if isinstance(analysis_result, list):
                # Old format - convert to new format
                pts = analysis_result
                params = []
            else:
                # New format
                pts = analysis_result.get('key_points', [])
                params = analysis_result.get('parameters', [])

            if not pts and extracted_text:
                analysis_result = analyze_report_for_key_points(extracted_text.encode('utf-8'), content_type, filename, conversation_text, patient_dict.get('sex', 'Male'), patient_dict.get('age', 30), p.language)
                pts = analysis_result.get('key_points', [])
                params = analysis_result.get('parameters', [])
                # Persist generated points
                try:
                    c.execute('UPDATE reports SET key_points = ? WHERE id = ?', (json.dumps(analysis_result), report_dict['id']))
                    c.commit()
                except:
                    pass

            if pts:
                report_key_points.extend(pts)
                reports_analysis.append({
                    'filename': filename,
                    'content_type': content_type,
                    'key_points': pts,
                    'parameters': params
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

    # Generate patient-friendly summary in patient's language (Phase 3)
    patient_summary_english = json.dumps(summary_data, indent=2)
    patient_summary_translated = translate_medical_summary(patient_summary_english, p.language)

    # Save visit record
    c.execute('INSERT INTO visits (patient_id, visit_date, summary, symptoms, risk, priority, created_at) VALUES (?,?,?,?,?,?,?)',
              (p.patient_id, datetime.now().isoformat(), json.dumps(summary_data), json.dumps(p.symptoms), risk, priority, datetime.now().isoformat()))
    c.commit()

    return {
        'patient_id': p.patient_id,
        'summary': summary_data,  # English version for doctors
        'patient_summary': patient_summary_translated,  # Translated version for patients
        'risk': risk,
        'priority': priority,
        'model': model,
        'reports_analysis': reports_analysis,
        'report_key_points': list(dict.fromkeys(report_key_points)),  # De-duplicate while preserving order
        'all_parameters': [param for report in reports_analysis for param in report.get('parameters', [])]  # Flatten all parameters
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
                'patient_id': patient_id,
                'assigned_doctor_id': entry.get('assigned_doctor_id'),
                'consultation_type': entry.get('consultation_type')
            })

            # Get assigned doctor info
            if entry.get('assigned_doctor_id'):
                doctor = c.execute('SELECT * FROM doctors WHERE id = ?', (entry['assigned_doctor_id'],)).fetchone()
                if doctor:
                    result['assigned_doctor'] = dict(doctor)

    return result

@app.post('/queue')
def add_to_queue(q: QueueIn):
    c = get_db()
    token = f"S-{datetime.now().strftime('%y%m%d%H%M%S')[:10]}-{c.execute('SELECT COUNT(*) FROM queue').fetchone()[0] + 1}"
    valid_priorities = ['low', 'medium', 'high']
    priority = q.priority if q.priority in valid_priorities else 'medium'

    # Phase 11.1: Auto-assign doctor based on symptoms/specialty matching
    assigned_doctor_id = match_doctor_specialty(q.symptoms)
    consultation_type = 'initial'

    c.execute('INSERT INTO queue (patient_id, token, priority, status, assigned_doctor_id, consultation_type, created_at) VALUES (?,?,?,?,?,?,?)',
              (q.patient_id, token, priority, 'waiting', assigned_doctor_id, consultation_type, datetime.now().isoformat()))
    c.commit()

    # Get assigned doctor info
    doctor = c.execute('SELECT * FROM doctors WHERE id = ?', (assigned_doctor_id,)).fetchone()

    return {
        'token': token,
        'priority': priority,
        'status': 'waiting',
        'assigned_doctor': dict(doctor) if doctor else None
    }

@app.patch('/queue/{queue_id}/status')
def update_queue_status(queue_id: int, status: Literal['waiting', 'in_consultation', 'completed']):
    c = get_db()
    c.execute('UPDATE queue SET status = ? WHERE id = ?', (status, queue_id))
    c.commit()
    return {'ok': True}

@app.patch('/queue/{queue_id}/reassign')
def reassign_doctor(queue_id: int, new_doctor_id: str = Query(...)):
    c = get_db()
    # Verify doctor exists
    doctor = c.execute('SELECT * FROM doctors WHERE id = ? AND is_active = 1', (new_doctor_id,)).fetchone()
    if not doctor:
        raise HTTPException(status_code=404, detail='Doctor not found or inactive')

    c.execute('UPDATE queue SET assigned_doctor_id = ? WHERE id = ?', (new_doctor_id, queue_id))
    c.commit()
    return {'ok': True, 'assigned_doctor': dict(doctor)}

@app.post('/queue/reassign-by-patient')
def reassign_doctor_by_patient(p: ReassignDoctorIn):
    """
    Phase 13.1: Reassign doctor by patient_id (more convenient for frontend).
    Finds the active queue entry for the patient and reassigns the doctor.
    """
    c = get_db()
    # Verify doctor exists
    doctor = c.execute('SELECT * FROM doctors WHERE id = ? AND is_active = 1', (p.new_doctor_id,)).fetchone()
    if not doctor:
        raise HTTPException(status_code=404, detail='Doctor not found or inactive')

    # Find active queue entry for patient
    queue_entry = c.execute(
        'SELECT id FROM queue WHERE patient_id = ? AND status IN (\'waiting\', \'in_consultation\') ORDER BY created_at DESC LIMIT 1',
        (p.patient_id,)
    ).fetchone()

    if not queue_entry:
        raise HTTPException(status_code=404, detail='No active queue entry found for patient')

    # Update the queue entry
    c.execute('UPDATE queue SET assigned_doctor_id = ? WHERE id = ?', (p.new_doctor_id, queue_entry[0]))
    c.commit()

    return {'ok': True, 'assigned_doctor': dict(doctor)}

@app.get('/patients/{patient_id}/visits')
def get_patient_visits(patient_id: str):
    c = get_db()
    visits = c.execute('SELECT * FROM visits WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    return [dict(v) for v in visits]

# --- Doctor Endpoints ---

@app.get('/doctors')
def get_doctors():
    c = get_db()
    doctors = c.execute('SELECT * FROM doctors WHERE is_active = 1 ORDER BY specialty, name').fetchall()
    return [dict(d) for d in doctors]

@app.get('/doctors/{doctor_id}')
def get_doctor(doctor_id: str):
    c = get_db()
    doctor = c.execute('SELECT * FROM doctors WHERE id = ?', (doctor_id,)).fetchone()
    if not doctor:
        raise HTTPException(status_code=404, detail='Doctor not found')
    return dict(doctor)

@app.post('/doctors/login')
def doctor_login(doctor_id: str = Query(...)):
    c = get_db()
    doctor = c.execute('SELECT * FROM doctors WHERE id = ? AND is_active = 1', (doctor_id,)).fetchone()
    if not doctor:
        raise HTTPException(status_code=404, detail='Doctor not found or inactive')
    return dict(doctor)

@app.get('/doctors/{doctor_id}/patients')
def get_doctor_patients(doctor_id: str):
    c = get_db()
    # Get patients in queue assigned to this doctor
    queue_patients = c.execute('''
        SELECT q.*, p.name as patient_name, p.age, p.phone
        FROM queue q
        JOIN patients p ON q.patient_id = p.id
        WHERE q.assigned_doctor_id = ? AND q.status IN ('waiting', 'in_consultation')
        ORDER BY q.created_at
    ''', (doctor_id,)).fetchall()
    return [dict(p) for p in queue_patients]

@app.get('/doctors/{doctor_id}/patients/{patient_id}/review')
def get_patient_review(doctor_id: str, patient_id: str):
    c = get_db()
    # Get patient details
    patient = c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
    if not patient:
        raise HTTPException(status_code=404, detail='Patient not found')

    # Get reports
    reports = c.execute('SELECT * FROM reports WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    reports_list = []
    for r in reports:
        r_dict = dict(r)
        if r_dict.get('key_points'):
            try:
                parsed = json.loads(r_dict['key_points'])
                # Handle both old format (list) and new format (dict)
                if isinstance(parsed, dict):
                    r_dict['key_points'] = parsed.get('key_points', [])
                    r_dict['parameters'] = parsed.get('parameters', [])
                else:
                    r_dict['key_points'] = parsed
                    r_dict['parameters'] = []
            except:
                r_dict['key_points'] = []
                r_dict['parameters'] = []
        else:
            r_dict['key_points'] = []
            r_dict['parameters'] = []
        reports_list.append(r_dict)

    # Get visit history
    visits = c.execute('SELECT * FROM visits WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    visits_list = []
    for v in visits:
        v_dict = dict(v)
        if v_dict.get('summary'):
            try:
                v_dict['summary'] = json.loads(v_dict['summary'])
            except:
                pass
        if v_dict.get('symptoms'):
            try:
                v_dict['symptoms'] = json.loads(v_dict['symptoms'])
            except:
                v_dict['symptoms'] = []
        visits_list.append(v_dict)

    # Get prescriptions
    prescriptions = c.execute('SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    prescriptions_list = []
    for p in prescriptions:
        p_dict = dict(p)
        if p_dict.get('medications'):
            try:
                p_dict['medications'] = json.loads(p_dict['medications'])
            except:
                p_dict['medications'] = []
        prescriptions_list.append(p_dict)

    return {
        'patient': dict(patient),
        'reports': reports_list,
        'visits': visits_list,
        'prescriptions': prescriptions_list
    }

# --- Prescription Endpoints ---

@app.post('/prescriptions')
def create_prescription(p: PrescriptionIn):
    c = get_db()
    cur = c.execute('''
        INSERT INTO prescriptions (patient_id, visit_id, doctor_id, doctor_notes, medications, created_at, language)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (p.patient_id, p.visit_id, p.doctor_id, p.doctor_notes, json.dumps(p.medications), datetime.now().isoformat(), p.language))
    c.commit()
    return {'prescription_id': cur.lastrowid, 'ok': True}

@app.get('/patients/{patient_id}/prescriptions')
def get_patient_prescriptions(patient_id: str):
    c = get_db()
    prescriptions = c.execute('SELECT * FROM prescriptions WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    result = []
    for p in prescriptions:
        p_dict = dict(p)
        if p_dict.get('medications'):
            try:
                p_dict['medications'] = json.loads(p_dict['medications'])
            except:
                p_dict['medications'] = []
        result.append(p_dict)
    return result

# --- Report Comparison Endpoints ---

@app.post('/patients/{patient_id}/reports/compare')
def compare_reports_api(patient_id: str, p: ReportComparisonIn):
    c = get_db()
    # Get both reports
    past_report = c.execute('SELECT * FROM reports WHERE id = ? AND patient_id = ?', (p.past_report_id, patient_id)).fetchone()
    present_report = c.execute('SELECT * FROM reports WHERE id = ? AND patient_id = ?', (p.present_report_id, patient_id)).fetchone()

    if not past_report or not present_report:
        raise HTTPException(status_code=404, detail='One or both reports not found')

    # Use AI to compare reports
    past_report_dict = dict(past_report)
    present_report_dict = dict(present_report)

    comparison_result = compare_reports(past_report_dict, present_report_dict, p.language)

    # Save comparison
    comparison_summary = {
        'past_report': {
            'id': past_report_dict['id'],
            'filename': past_report_dict['filename'],
            'created_at': past_report_dict['created_at']
        },
        'present_report': {
            'id': present_report_dict['id'],
            'filename': present_report_dict['filename'],
            'created_at': present_report_dict['created_at']
        },
        'comparison': comparison_result['comparison'],
        'summary': comparison_result['summary'],
        'notes': comparison_result['notes']
    }

    cur = c.execute('''
        INSERT INTO report_comparisons (patient_id, past_report_id, present_report_id, comparison_summary, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (patient_id, p.past_report_id, p.present_report_id, json.dumps(comparison_summary), datetime.now().isoformat()))
    c.commit()

    return comparison_summary

@app.get('/patients/{patient_id}/report-comparisons')
def get_report_comparisons(patient_id: str):
    c = get_db()
    comparisons = c.execute('SELECT * FROM report_comparisons WHERE patient_id = ? ORDER BY created_at DESC', (patient_id,)).fetchall()
    result = []
    for comp in comparisons:
        comp_dict = dict(comp)
        if comp_dict.get('comparison_summary'):
            try:
                comp_dict['comparison_summary'] = json.loads(comp_dict['comparison_summary'])
            except:
                pass
        result.append(comp_dict)
    return result

# --- Handwritten Report OCR (Phase 9) ---

def extract_handwritten_text(image_content: bytes, content_type: str, language: str = 'English') -> dict:
    """
    Extract text from handwritten prescription/report using OpenAI GPT-4o Vision.
    Returns structured data with extracted text and fields.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return {
            'extracted_text': 'OCR unavailable - API not configured',
            'structured_data': {}
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        base64_img = base64.b64encode(image_content).decode('utf-8')
        mime = content_type

        system_prompt = """You are a medical document OCR specialist specializing in handwritten prescriptions and medical reports.
Extract all text from the image and structure it appropriately.

CRITICAL RULES:
1. Extract ALL text visible in the image, including handwriting
2. If it's a prescription, identify: medication names, dosages, frequency, duration
3. If it's a report, identify: patient info, findings, diagnoses, recommendations
4. Return a JSON object with:
   - "extracted_text": all text as a single string
   - "medications": array of {name, dosage, frequency, duration} if applicable
   - "diagnosis": diagnosis or findings if applicable
   - "notes": any additional notes or instructions
5. Preserve the original language of the document
6. If unsure about any field, leave it empty but include what you can extract

Return ONLY the JSON object, no explanations."""

        user_prompt = f"""Extract and structure the text from this medical document in {language} if possible, otherwise preserve original language.
Focus on medications, dosages, and any medical findings."""

        response = client.chat.completions.create(
            model='gpt-4o',
            temperature=0.2,
            response_format={'type': 'json_object'},
            max_tokens=1000,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': user_prompt},
                        {'type': 'image_url', 'image_url': {'url': f"data:{mime};base64,{base64_img}"}}
                    ]
                }
            ]
        )

        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"Handwritten OCR error: {e}")
        return {
            'extracted_text': 'OCR extraction failed',
            'structured_data': {},
            'error': str(e)
        }

@app.post('/doctors/upload-handwritten')
async def upload_handwritten_report(report: UploadFile = File(...), patient_id: str = Query(...), language: str = Query('English')):
    """
    Phase 9.1: Upload handwritten prescription/report for OCR extraction.
    Accepts image file and returns extracted text with structured data.
    """
    if report.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return {'ok': False, 'error': 'Only JPG, PNG, and WebP images are supported for handwritten OCR'}

    content = await report.read()
    max_size = 5 * 1024 * 1024  # 5MB
    if len(content) > max_size:
        return {'ok': False, 'error': 'File size exceeds 5MB limit'}

    # Extract text using GPT-4o Vision
    extraction_result = extract_handwritten_text(content, report.content_type, language)

    return {
        'ok': True,
        'filename': report.filename,
        'extracted_text': extraction_result.get('extracted_text', ''),
        'structured_data': extraction_result,
        'image_preview': f"data:{report.content_type};base64,{base64.b64encode(content).decode('utf-8')}"
    }

# --- Patient Report Generation (Phase 10) ---

def generate_patient_report(patient_id: str, doctor_id: str, doctor_notes: str, medications: list[dict], diagnosis: str, language: str = 'English') -> dict:
    """
    Generate a comprehensive patient report in patient's language using AI.
    Includes patient info, doctor notes, prescription, and summary.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        return {
            'report_content': 'Report generation unavailable - API not configured',
            'error': 'OpenAI API not configured'
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)

        # Get patient info
        c = get_db()
        patient = c.execute('SELECT * FROM patients WHERE id = ?', (patient_id,)).fetchone()
        if not patient:
            return {'error': 'Patient not found'}

        patient_dict = dict(patient)
        doctor = c.execute('SELECT * FROM doctors WHERE id = ?', (doctor_id,)).fetchone()
        doctor_dict = dict(doctor) if doctor else {'name': 'Unknown Doctor', 'specialty': 'General Medicine'}

        # Build medications text
        medications_text = ""
        if medications:
            for med in medications:
                medications_text += f"- {med.get('name', 'Unknown')}: {med.get('dosage', '')} {med.get('frequency', '')} for {med.get('duration', '')}\n"

        system_prompt = f"""You are a medical report generator. Generate a comprehensive patient report in {language}.

CRITICAL RULES:
1. Write the report in {language} (use patient's preferred language)
2. Keep medical terminology accurate but use patient-friendly language
3. Structure the report with clear sections:
   - Patient Information
   - Doctor Information
   - Consultation Summary
   - Diagnosis
   - Prescription/Medications
   - Doctor's Notes
   - Follow-up Instructions
4. Be clear, professional, and empathetic
5. Include all provided information
6. Add appropriate follow-up instructions based on the diagnosis

Return the complete report as plain text (no markdown formatting)."""

        user_prompt = f"""Generate a patient report with the following information:

PATIENT INFORMATION:
- Name: {patient_dict.get('name', 'Unknown')}
- Age: {patient_dict.get('age', 'Unknown')}
- Sex: {patient_dict.get('sex', 'Unknown')}
- Patient ID: {patient_id}

DOCTOR INFORMATION:
- Name: {doctor_dict.get('name', 'Unknown')}
- Specialty: {doctor_dict.get('specialty', 'General Medicine')}
- Doctor ID: {doctor_id}

CONSULTATION DETAILS:
- Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

DIAGNOSIS:
{diagnosis or 'Not specified'}

PRESCRIPTION/MEDICATIONS:
{medications_text or 'No medications prescribed'}

DOCTOR'S NOTES:
{doctor_notes or 'No additional notes'}

Generate a complete report in {language}."""

        response = client.chat.completions.create(
            model='gpt-4o-mini',
            temperature=0.3,
            max_tokens=1500,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )

        report_content = response.choices[0].message.content.strip()

        return {
            'report_content': report_content,
            'language': language,
            'generated_at': datetime.now().isoformat(),
            'patient_name': patient_dict.get('name', 'Unknown'),
            'doctor_name': doctor_dict.get('name', 'Unknown')
        }

    except Exception as e:
        print(f"Report generation error: {e}")
        return {
            'report_content': 'Report generation failed',
            'error': str(e)
        }

@app.post('/doctors/{doctor_id}/patients/{patient_id}/generate-report')
def generate_report_endpoint(doctor_id: str, patient_id: str, p: GenerateReportIn):
    """
    Phase 10.1: Generate patient report in patient's language.
    Accepts doctor notes, medications, diagnosis and returns formatted report.
    """
    result = generate_patient_report(
        patient_id=patient_id,
        doctor_id=doctor_id,
        doctor_notes=p.doctor_notes,
        medications=p.medications,
        diagnosis=p.diagnosis,
        language=p.language
    )

    return result

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
