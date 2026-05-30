# EvalForge — Deployment Guide
# Railway (Backend) + Vercel (Frontend) + Supabase (DB) + Upstash (Redis)
# All FREE tier — $0/month

---

## Architecture on Free Tier

```
Internet
   │
   ├── Vercel (Frontend - Next.js)          FREE
   │      └── evalforge.vercel.app
   │
   └── Railway (Backend)                    FREE ($5 credit/mo)
          ├── evalforge-api (FastAPI)
          └── evalforge-worker (Celery)
                    │
          ┌─────────┴──────────┐
          │                    │
     Supabase              Upstash Redis
     (PostgreSQL)          (Job queue)
         FREE                  FREE
       500MB                  10k req/day
```

---

## Step 1 — Supabase (PostgreSQL + pgvector)

### 1a. Create project
1. Go to https://supabase.com → Sign up free
2. New Project → name it `evalforge`
3. Choose region closest to you (Mumbai for India)
4. Set a strong database password → **save it**
5. Wait ~2 minutes for provisioning

### 1b. Get connection strings
1. Settings → Database → Connection string
2. Copy **URI** — two versions needed:

```bash
# Async (for FastAPI app)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres

# Sync (for Alembic migrations)
DATABASE_URL_SYNC=postgresql://postgres.[ref]:[password]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
```

> ⚠️ Use **Session mode** (port 5432) not Transaction mode (port 6543) for migrations

### 1c. pgvector is pre-installed on Supabase ✅
No extra setup — Supabase includes pgvector by default.

### 1d. Run migrations from local machine
```bash
cd backend
# Set DATABASE_URL_SYNC in your .env to the Supabase URL
alembic upgrade head
python seed.py   # optional: creates demo user
```

---

## Step 2 — Upstash Redis (Job Queue)

### 2a. Create database
1. Go to https://upstash.com → Sign up free
2. Create Database → name `evalforge-redis`
3. Region: same as Supabase
4. Type: Regional (free)

### 2b. Get Redis URL
1. Dashboard → your database → Details
2. Copy **REDIS_URL** (looks like `redis://default:xxxxx@xxxxx.upstash.io:6379`)

---

## Step 3 — Railway (FastAPI + Celery)

### 3a. Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### 3b. Create project
```bash
cd evalforge/backend
railway init
# Select: Create new project
# Name: evalforge
```

### 3c. Deploy API service
```bash
railway up --service evalforge-api
```

### 3d. Set environment variables (API service)
In Railway dashboard → evalforge-api → Variables, add ALL of these:

```bash
# Database (from Supabase)
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[pass]@...supabase.com:5432/postgres
DATABASE_URL_SYNC=postgresql://postgres.[ref]:[pass]@...supabase.com:5432/postgres

# Redis (from Upstash)
REDIS_URL=redis://default:xxxxx@xxxxx.upstash.io:6379

# Auth (generate with: openssl rand -hex 32)
JWT_SECRET=your-64-char-random-hex-string-here-never-share-this
ENCRYPTION_KEY=your-32-char-string-for-aes-encryption!!

# LLM
OPENAI_API_KEY=sk-...

# App
ENVIRONMENT=production
FRONTEND_URL=https://evalforge.vercel.app
LOG_LEVEL=INFO

# Stripe (Phase 4 — add later)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# Email (Resend — free 100 emails/day)
RESEND_API_KEY=re_...
EMAIL_FROM=noreply@yourdomain.com
```

### 3e. Set start command
Railway dashboard → evalforge-api → Settings → Start command:
```
bash start.sh
```
This runs migrations then starts the API.

### 3f. Deploy Celery worker (separate service)
```bash
# Create a second service from same repo
railway up --service evalforge-worker
```

Worker service Variables — same as API service PLUS:
```bash
# Override start command for worker:
# Railway dashboard → evalforge-worker → Settings → Start command:
# celery -A celery_worker worker --loglevel=info --concurrency=2
```

### 3g. Get your API URL
Railway dashboard → evalforge-api → Settings → Networking → Generate Domain
Copy the URL: `https://evalforge-api-production.up.railway.app`

### 3h. Verify deployment
```bash
curl https://evalforge-api-production.up.railway.app/health
# Should return: {"status": "ok", "version": "0.1.0"}

# Full API docs:
# https://evalforge-api-production.up.railway.app/docs
```

---

## Step 4 — Vercel (Next.js Frontend)

### 4a. Push to GitHub first
```bash
cd evalforge
git init
git add .
git commit -m "feat: initial EvalForge implementation"
git remote add origin https://github.com/YOUR_USERNAME/evalforge
git push -u origin main
```

### 4b. Deploy to Vercel
```bash
cd frontend
npx vercel
# Follow prompts:
# - Link to existing project? No
# - What's your project name? evalforge
# - Which directory? ./   (you're already in frontend/)
# - Override settings? No
```

OR connect via Vercel dashboard:
1. vercel.com → New Project → Import from GitHub
2. Select your `evalforge` repo
3. Set **Root Directory** to `frontend`
4. Framework: Next.js (auto-detected)

### 4c. Set environment variables in Vercel
Vercel dashboard → evalforge → Settings → Environment Variables:

```bash
NEXTAUTH_URL=https://evalforge.vercel.app
NEXTAUTH_SECRET=your-nextauth-secret-min-32-chars-random

GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret

NEXT_PUBLIC_API_URL=https://evalforge-api-production.up.railway.app
```

### 4d. Google OAuth setup (for login)
1. console.cloud.google.com → New Project → `evalforge`
2. APIs & Services → OAuth consent screen → External → Fill basics
3. Credentials → Create OAuth 2.0 Client ID
4. Authorized redirect URIs:
   ```
   https://evalforge.vercel.app/api/auth/callback/google
   http://localhost:3000/api/auth/callback/google
   ```
5. Copy Client ID + Secret → paste into Vercel env vars

### 4e. Final deploy
```bash
npx vercel --prod
```

Your app is live at: **https://evalforge.vercel.app** 🎉

---

## Step 5 — Post-deployment verification

```bash
# 1. Health check
curl https://evalforge-api-production.up.railway.app/health

# 2. Register a user
curl -X POST https://evalforge-api-production.up.railway.app/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass","name":"Your Name"}'

# 3. Login
curl -X POST https://evalforge-api-production.up.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}'

# 4. Visit frontend
open https://evalforge.vercel.app
```

---

## Custom Domain (optional, free on Vercel)

1. Vercel → evalforge → Settings → Domains → Add domain
2. Add `evalforge.yourdomain.com`
3. Add CNAME record at your DNS provider:
   ```
   CNAME evalforge → cname.vercel-dns.com
   ```
4. Update `NEXTAUTH_URL` and `FRONTEND_URL` env vars

---

## Monitoring (free)

### Railway logs
```bash
railway logs --service evalforge-api
railway logs --service evalforge-worker
```

### Sentry (error tracking — free 5k errors/mo)
1. sentry.io → New Project → FastAPI
2. Copy DSN → add to Railway env: `SENTRY_DSN=https://...`

---

## Estimated Free Tier Usage

| Service | Monthly usage | Free limit | Cost |
|---------|-------------|------------|------|
| Vercel | ~1GB bandwidth | 100GB | $0 |
| Railway | ~200 compute hours | $5 credit | $0 |
| Supabase | ~50MB DB | 500MB | $0 |
| Upstash | ~5k Redis ops | 10k/day | $0 |
| OpenAI | ~1000 judge calls | Pay-per-use | ~$2 |

**Total: ~$2/month** (only OpenAI API usage)

---

## Environment Variables Checklist

Before going live, confirm all of these are set in Railway:

- [ ] `DATABASE_URL` (async, asyncpg://)
- [ ] `DATABASE_URL_SYNC` (sync, postgresql://)
- [ ] `REDIS_URL`
- [ ] `JWT_SECRET` (64+ chars, random)
- [ ] `ENCRYPTION_KEY` (32 chars, random)
- [ ] `OPENAI_API_KEY`
- [ ] `ENVIRONMENT=production`
- [ ] `FRONTEND_URL` (your Vercel URL)

And in Vercel:
- [ ] `NEXTAUTH_URL` (your Vercel URL)
- [ ] `NEXTAUTH_SECRET` (32+ chars, random)
- [ ] `NEXT_PUBLIC_API_URL` (your Railway API URL)
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
