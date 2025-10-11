# OAuth Configuration Guide

This guide explains how to configure Google and HubSpot OAuth for the Financial Advisor AI application.

## Google OAuth Setup

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Gmail API
   - Google Calendar API
   - Google+ API (for user info)

### 2. Configure OAuth Consent Screen
1. Navigate to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in application details:
   - App name: Financial Advisor AI
   - User support email: your email
   - Developer contact: your email
4. Add scopes:
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar`
5. **Add test user:** `webshookeng@gmail.com` (REQUIRED)

### 3. Create OAuth 2.0 Credentials
1. Navigate to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. Application type: "Web application"
4. Name: Financial Advisor AI Web Client
5. Authorized redirect URIs:
   - Development: `http://localhost:8000/auth/google/callback`
   - Production: `https://your-domain.com/auth/google/callback`
6. Save and copy:
   - Client ID → `GOOGLE_CLIENT_ID`
   - Client Secret → `GOOGLE_CLIENT_SECRET`

## HubSpot OAuth Setup

### 1. Create HubSpot Developer Account
1. Go to [HubSpot Developers](https://developers.hubspot.com/)
2. Sign up or log in
3. Create a free testing account

### 2. Create App
1. Navigate to "Apps" in developer account
2. Click "Create app"
3. Fill in app details:
   - App name: Financial Advisor AI
   - Description: AI agent for financial advisors

### 3. Configure OAuth
1. Go to "Auth" tab in your app
2. Add redirect URL:
   - Development: `http://localhost:8000/auth/hubspot/callback`
   - Production: `https://your-domain.com/auth/hubspot/callback`
3. Select scopes:
   - `crm.objects.contacts.read`
   - `crm.objects.contacts.write`
   - `crm.objects.companies.read`
   - `crm.objects.companies.write`
4. Save and copy:
   - Client ID → `HUBSPOT_CLIENT_ID`
   - Client Secret → `HUBSPOT_CLIENT_SECRET`

## Environment Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=<your_google_client_id>
GOOGLE_CLIENT_SECRET=<your_google_client_secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# HubSpot OAuth
HUBSPOT_CLIENT_ID=<your_hubspot_client_id>
HUBSPOT_CLIENT_SECRET=<your_hubspot_client_secret>
HUBSPOT_REDIRECT_URI=http://localhost:8000/auth/hubspot/callback

# Application
SECRET_KEY=<generate_a_secure_random_key_min_32_chars>
FRONTEND_URL=http://localhost:3000
```

### Generate SECRET_KEY

You can generate a secure secret key using Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

## Testing OAuth Flows

### Google OAuth Flow
1. Start the backend server: `uvicorn app.main:app --reload`
2. Visit: `http://localhost:8000/auth/google/start`
3. You should be redirected to Google consent screen
4. Log in with `webshookeng@gmail.com` (must be added as test user)
5. Grant permissions
6. You'll be redirected back with a session cookie

### HubSpot OAuth Flow
1. Ensure you're already authenticated with Google (have session cookie)
2. Visit: `http://localhost:8000/auth/hubspot/start`
3. You should be redirected to HubSpot authorization page
4. Grant permissions
5. You'll be redirected back and HubSpot tokens will be stored

## Token Refresh

Tokens are automatically refreshed when they expire:
- **Google**: Uses refresh token to get new access token
- **HubSpot**: Uses refresh token to get new access token

Both refresh mechanisms are implemented in `app/utils/oauth_helpers.py`.

## Security Notes

1. **CSRF Protection**: All OAuth flows use state parameter for CSRF protection
2. **Session Cookies**: httpOnly cookies with SameSite=Lax
3. **Token Storage**: Tokens stored in database as JSON (encrypt in production!)
4. **HTTPS**: Use HTTPS in production for secure cookie transmission

## Troubleshooting

### "redirect_uri_mismatch" error
- Verify redirect URIs match exactly in OAuth console and .env file
- Include protocol (http/https) and port if not 80/443

### "access_denied" error
- User canceled authorization
- Check if user is added as test user (for Google)

### "invalid_client" error
- Check CLIENT_ID and CLIENT_SECRET are correct
- Ensure credentials are for correct environment (dev/prod)

### Token refresh fails
- Refresh token may have been revoked
- User needs to re-authorize application
