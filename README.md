# Synapse AI - Hospital/Patient Management Prototype

A Next.js frontend prototype with a local FastAPI backend for hospital/patient intake workflow.

## Features

- **Frontend**: Next.js 16 App Router, React 19, TypeScript with neo-brutalist design
- **Backend**: FastAPI with in-memory SQLite database
- **AI Integration**:
  - OpenAI GPT-4o-mini for conversational follow-up questions
  - OpenAI GPT-4o-mini for clinician handoff summaries
- **Priority System**: Automatic priority calculation based on vitals and symptoms
- **Queue Management**: Real-time queue tracking with status updates
- **Visit History**: Patient visit records and history retrieval

## Setup

### Prerequisites

- Python 3.14+
- Node.js 18+
- pnpm 12.3.4

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
py -m pip install -r requirements.txt
```

3. The `.env` file is already configured with your API key:
   - `OPENAI_API_KEY`: For OpenAI API (used for both follow-up questions and summaries)

4. Start the backend server:
```bash
py main.py
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
```bash
pnpm install
```

2. Start the development server:
```bash
pnpm dev
```

The frontend will run on `http://localhost:3000`

## API Endpoints

### Patients
- `POST /patients` - Create new patient
- `GET /patients/{patient_id}` - Get patient by ID
- `GET /patients/{patient_id}/reports` - List patient reports
- `DELETE /patients/{patient_id}/reports/{report_id}` - Delete report

### Conversation
- `POST /conversation/next` - Get AI follow-up question (OpenAI GPT-4o-mini)
- `POST /summary` - Generate clinician handoff summary (OpenAI GPT-4o-mini)

### Queue
- `GET /queue` - Get queue status (optional `?patient_id=` for individual info)
- `POST /queue` - Add patient to queue
- `PATCH /queue/{queue_id}/status` - Update queue status

### Visits
- `GET /patients/{patient_id}/visits` - Get patient visit history

### Health
- `GET /health` - Health check

## Database

The backend uses **in-memory SQLite** for development. Data resets when the server restarts.

Tables:
- `patients` - Patient records
- `reports` - Uploaded medical reports
- `visits` - Visit history with summaries
- `queue` - Queue entries with status tracking

## Priority Calculation

Priority is automatically calculated based on:
- **Vitals**: Blood pressure, blood sugar, temperature thresholds
- **Symptoms**: High-risk (breathlessness, chest pain) and moderate-risk symptoms

Returns: `low`, `medium`, or `high`

## Environment Variables

```env
OPENAI_API_KEY=your_openai_api_key
```

## Development Notes

- This is a prototype, not production medical software
- Clinical decisions must remain with qualified healthcare professionals
- OpenAI GPT-4o-mini is used for all AI features (follow-up questions and summaries)
- All AI features have fallback implementations if the API fails

## Tech Stack

### Frontend
- Next.js 16.4.0
- React 19
- TypeScript
- Tailwind CSS v4
- shadcn/ui components
- Lucide React icons
- qrcode.react

### Backend
- FastAPI
- Uvicorn
- Pydantic
- SQLite (in-memory)
- OpenAI SDK
- python-dotenv
