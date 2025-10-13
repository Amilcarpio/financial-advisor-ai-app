# Financial Advisor AI - Frontend

Frontend for Financial Advisor AI, built with React, TypeScript, Vite, and Tailwind CSS.

## Features
- Modern chat interface with streaming responses
- Google OAuth login
- HubSpot CRM connection
- Memory rules management
- Responsive design

## Getting Started (Development)

### Prerequisites
- Node.js 18+
- npm or yarn
- Backend API running (see backend/README.md)

### 1. Clone the repository
```bash
git clone https://github.com/Amilcarpio/financial-advisor-ai-app.git
cd financial-advisor-ai-app/frontend
```

### 2. Configure environment variables
Copy the example file and fill in your backend URL if needed:
```bash
cp .env.example .env
```

Example `.env.example`:
```env
# Local development
VITE_API_BASE_URL=http://localhost:8000

### 3. Install dependencies
```bash
npm install
```

### 4. Start development server
```bash
npm run dev
```

- App: http://localhost:5173

## Development Tips
- Use the provided `.env.example` as a template
- Never commit real secrets or production URLs
- For production deploy, see the confidential `DEPLOYMENT.md` (not in repo)

## License
Proprietary and confidential. Unauthorized copying or distribution is prohibited.

