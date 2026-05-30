# GitHub Actions — Secrets Setup Guide

Go to: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

## Required Secrets

| Secret name | Where to get it | Example |
|-------------|----------------|---------|
| `RAILWAY_TOKEN` | Railway dashboard → Account → API Tokens | `railway_...` |
| `VERCEL_TOKEN` | vercel.com → Settings → Tokens | `vercel_...` |
| `VERCEL_ORG_ID` | Run `vercel env ls` or check `.vercel/project.json` | `team_...` |
| `VERCEL_PROJECT_ID` | `.vercel/project.json` after first deploy | `prj_...` |
| `API_HEALTH_URL` | Your Railway API URL | `https://evalforge-api.railway.app` |
| `FRONTEND_URL` | Your Vercel URL | `https://evalforge.vercel.app` |
| `SLACK_WEBHOOK_URL` | Slack → Apps → Incoming Webhooks (optional) | `https://hooks.slack.com/...` |

## How to get Railway token

```bash
# Option 1: CLI
railway login
railway whoami   # confirms login

# Option 2: Dashboard
# railway.app → Account Settings → API Tokens → Create token
# Name: "GitHub Actions"
# Copy the token → paste as RAILWAY_TOKEN secret
```

## How to get Vercel IDs

```bash
cd evalforge/frontend
npx vercel link   # links project
cat .vercel/project.json
# Output:
# { "orgId": "team_XXXX", "projectId": "prj_XXXX" }
```

Copy `orgId` → `VERCEL_ORG_ID`
Copy `projectId` → `VERCEL_PROJECT_ID`

## Verify secrets work

After adding secrets, push any commit to main and watch:
GitHub repo → Actions → CI / CD Pipeline

Green checkmarks on all 8 jobs = everything is working.

## CI/CD Flow Summary

```
Push to main
     │
     ├── backend-tests     (pytest + coverage)
     ├── backend-lint      (ruff)
     ├── frontend-build    (tsc + next build)
     ├── migration-check   (upgrade + downgrade + upgrade)
     └── security-scan     (bandit + safety)
          │
          (all pass)
          │
     ├── deploy-backend    (Railway API + Worker)
     └── deploy-frontend   (Vercel)
          │
          (any fail on main)
          │
     └── notify-failure    (Slack alert)
```

PR Flow:
```
Open PR
     │
     └── validate          (tests + build — must pass to merge)
          │
          └── Posts comment on PR with pass/fail status
```

Nightly (2 AM UTC):
```
     └── health-check      (ping /health + frontend)
          │
          (fail)
          │
          └── Slack alert
```
