# Sprint 1 setup: identity and profile persistence

## Required services

1. Python 3.12+ and a virtual environment in `backend/.venv`.
2. PostgreSQL database used by `DATABASE_URL`.
3. A Google Cloud OAuth web application.

## Configure Google OAuth

In Google Cloud Console, create an OAuth 2.0 Client ID of type **Web application** and add exactly:

`http://localhost:8000/v1/auth/google/callback`

For a deployed environment, add its HTTPS callback as a separate URI. Do not use a wildcard callback URI.

## Environment variables

Copy `backend/.env.sprint1.example` to `backend/.env` and set:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `SESSION_SECRET` (a cryptographically random value of at least 32 bytes)
- `GOOGLE_REDIRECT_URI`
- `FRONTEND_URL`
- `DATABASE_URL`

Never commit `.env` or send secret values in a chat.

## Database migration

Back up the database, then run:

```powershell
Get-Content migrations/0001_frontend_identity_and_profile.sql | psql $env:DATABASE_URL
```

The migration adds Google identity fields and draft/profile version metadata. It does not remove or rewrite existing user data.
