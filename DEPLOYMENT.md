# Deployment Guide - Synapse AI

This guide explains how to deploy Synapse AI using Vercel (frontend) and Render (backend).

## Prerequisites

- GitHub repository with Synapse AI code
- OpenAI API key
- Accounts on:
  - [Vercel](https://vercel.com) (free)
  - [Render](https://render.com) (free tier available)

---

## Step 1: Deploy Backend to Render

### 1.1 Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (recommended)

### 1.2 Create New Web Service
1. Click "New +" → "Web Service"
2. Select your `SYNAPSE` repository
3. Configure settings:

**Basic Settings:**
- **Name**: `synapse-backend`
- **Region**: Choose nearest region (e.g., Oregon)
- **Branch**: `main`

**Build & Deploy:**
- **Root Directory**: `backend`
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Advanced:**
- **Instance Type**: `Free` (or paid for better performance)

### 1.3 Add Environment Variables
In the "Environment" section, add:

```
OPENAI_API_KEY=your_actual_openai_api_key_here
PORT=8000
```

### 1.4 Deploy
1. Click "Create Web Service"
2. Wait for deployment (2-3 minutes)
3. Once deployed, you'll get a URL like: `https://synapse-backend.onrender.com`
4. **Copy this URL** - you'll need it for the frontend

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Create Vercel Account
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub (recommended)

### 2.2 Import Repository
1. Click "Add New Project" → "Import Git Repository"
2. Select your `SYNAPSE` repository
3. Configure settings:

**Framework Preset:**
- **Framework**: Next.js
- **Project Name**: `synapse-ai`

**General:**
- **Root Directory**: `.` (leave as is)
- **Build Command**: `pnpm build`
- **Output Directory**: `.next`
- **Install Command**: `pnpm install`

### 2.3 Add Environment Variables
In the "Environment Variables" section, add:

```
NEXT_PUBLIC_API_URL=https://synapse-backend.onrender.com
```

**Replace `synapse-backend.onrender.com` with your actual Render backend URL from Step 1.4**

### 2.4 Deploy
1. Click "Deploy"
2. Wait for deployment (1-2 minutes)
3. Once deployed, you'll get a URL like: `https://synapse-ai.vercel.app`

---

## Step 3: Important Configuration Updates

### 3.1 Update Backend for Production
Edit `backend/main.py` to use file-based database:

```python
# Change this line:
DB_PATH = ':memory:'

# To this:
DB_PATH = 'synapse.db'
```

**Why?** In-memory database resets on every restart. File-based database persists data.

### 3.2 Update CORS for Production
In `backend/main.py`, update the CORS middleware:

```python
# Change this:
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

# To this (after frontend is deployed):
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://synapse-ai.vercel.app', 'http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)
```

**Replace `synapse-ai.vercel.app` with your actual Vercel frontend URL.**

### 3.3 Push Changes to GitHub
```bash
git add .
git commit -m "Configure for production deployment"
git push origin main
```

Render and Vercel will automatically redeploy with the new changes.

---

## Step 4: Verify Deployment

### 4.1 Test Backend
1. Go to your Render backend URL: `https://synapse-backend.onrender.com`
2. Visit `/health` endpoint: `https://synapse-backend.onrender.com/health`
3. Should return: `{"ok": true, "service": "synapse-ai"}`

### 4.2 Test Frontend
1. Go to your Vercel frontend URL: `https://synapse-ai.vercel.app`
2. Try the patient registration flow
3. Verify API calls work (check browser console for errors)

---

## Step 5: Post-Deployment Setup

### 5.1 Enable HTTPS
Both Vercel and Render provide HTTPS automatically - no action needed.

### 5.2 Monitor Deployments
- **Render**: Dashboard shows logs, deployment status
- **Vercel**: Dashboard shows builds, analytics

### 5.3 Database Backups (Production)
For file-based SQLite, consider:
- Use Render's disk persistence
- Or migrate to PostgreSQL (Render offers free PostgreSQL)

---

## Troubleshooting

### Issue: Frontend can't connect to backend
**Solution:**
1. Check `NEXT_PUBLIC_API_URL` is correct in Vercel
2. Check CORS settings in backend
3. Check Render logs for errors

### Issue: Database resets on every deploy
**Solution:**
1. Change `DB_PATH` from `:memory:` to `synapse.db`
2. Push changes to GitHub
3. Render will redeploy with persistent database

### Issue: Build fails on Vercel
**Solution:**
1. Check Vercel build logs
2. Ensure `package.json` has correct scripts
3. Try: `pnpm install` → `pnpm build` locally first

### Issue: Build fails on Render
**Solution:**
1. Check Render build logs
2. Ensure `requirements.txt` has all dependencies
3. Try: `pip install -r requirements.txt` locally first

---

## Cost Estimate

### Free Tier (Recommended for Testing)
- **Render**: Free tier available (limited resources)
- **Vercel**: Free tier available (100GB bandwidth/month)

### Paid Tier (Production)
- **Render**: ~$7/month for basic web service
- **Vercel**: ~$20/month for production ( Hobby plan)

---

## Next Steps

1. Deploy backend to Render ✅
2. Deploy frontend to Vercel ✅
3. Update environment variables ✅
4. Test end-to-end flow ✅
5. Monitor performance ✅
6. Scale as needed ✅

---

## Support

- **Vercel Docs**: https://vercel.com/docs
- **Render Docs**: https://render.com/docs
- **Next.js Deployment**: https://nextjs.org/docs/deployment
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
