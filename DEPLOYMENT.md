# Vercel Deployment Guide

## Step 1: Initialize Git (if not already done)
```bash
cd /Users/abhishekgawade/Documents/VIDEO\ AI
git init
git add .
git commit -m "Initial commit: Vixa Studio AI Image"
```

## Step 2: Create GitHub Repository
1. Go to https://github.com/new
2. Create a new repository (e.g., `vixa-studio-ai`)
3. Push your code:
```bash
git remote add origin https://github.com/YOUR_USERNAME/vixa-studio-ai.git
git branch -M main
git push -u origin main
```

## Step 3: Deploy to Vercel

### Option A: Using Vercel CLI (Recommended)
```bash
npm install -g vercel
vercel
```
Follow the prompts:
- Link to your GitHub repository
- Choose framework: "Other"
- Set Root Directory: `.`
- Add Environment Variables (see below)

### Option B: Using Vercel Dashboard
1. Go to https://vercel.com
2. Sign up with GitHub
3. Click "New Project"
4. Select your GitHub repository
5. Click "Deploy"
6. Add Environment Variables (see below)

## Step 4: Add Environment Variables

In Vercel Dashboard:
1. Go to Project Settings → Environment Variables
2. Add:
   - `OPENAI_API_KEY` = your-api-key

Or via CLI during setup, enter when prompted.

## Key Files for Deployment:

✅ `vercel.json` - Already configured
✅ `requirements.txt` - Python dependencies
✅ `app.py` - Flask app (Vercel-ready)
✅ `index.html` - Frontend
✅ `.env` - Local only (add to .gitignore)

## Important Notes:

⚠️ **Do NOT commit .env file to Git!**
- Add API keys only in Vercel Dashboard Environment Variables
- Use .gitignore to exclude: .env, outputs/, __pycache__/

🔒 **API Credits:**
- DALL-E 3: $0.080 per 1024x1024 image
- GPT-4o mini: $0.015 per 1K input tokens
- Monitor usage in OpenAI Dashboard

📊 **URL Format after deployment:**
```
https://YOUR-PROJECT-NAME.vercel.app
```

## Troubleshooting:

If deployment fails:
1. Check Vercel logs: `vercel logs`
2. Ensure Python 3.9+ is used
3. Verify all dependencies in requirements.txt
4. Check OPENAI_API_KEY is set in Environment Variables

