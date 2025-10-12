# Financial Advisor AI - Frontend

React + TypeScript + Vite frontend for the Financial Advisor AI application with a modern, responsive chat interface.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The app will be available at `http://localhost:5173`

## 📋 Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running at `http://localhost:8000` (or configured via VITE_API_URL)

## 🔧 Configuration

### Environment Variables

Create a `.env.local` file in the frontend directory (optional):

```bash
# API endpoint (defaults to http://localhost:8000)
VITE_API_URL=http://localhost:8000

# Enable debug mode
VITE_DEBUG=true
```

The app automatically detects the backend URL, so configuration is only needed for custom setups.

## ✨ Features

### Authentication
- 🔐 **Google OAuth Integration** - Secure login with Google accounts
- 🍪 **Session Management** - httpOnly cookies for security
- 👤 **User Profile** - Display name and avatar from Google
- 🔗 **HubSpot Connection** - Optional CRM integration

### Chat Interface
- 💬 **Real-time Streaming** - Live AI responses with typing indicators
- 🤖 **Function Calling** - Visual feedback when AI uses tools
- 📝 **Example Prompts** - Quick-start suggestions for users
- 💾 **Chat History** - Save and load previous conversations (coming soon)
- 📱 **Mobile Responsive** - Works perfectly on all screen sizes

### UI/UX
- 🎨 **Modern Design** - Clean, professional interface
- 🌙 **Smooth Animations** - Hover effects and transitions
- ♿ **Accessibility** - Keyboard navigation and ARIA labels
- 🎯 **Smart Tooltips** - Helpful hints for disabled features
- 🔄 **Tab Navigation** - Switch between Chat and History views

### Components
- **ChatWindow** - Message display with streaming support
- **Composer** - Message input with future file upload support
- **MessageBubble** - Individual message rendering
- **NotFound** - Custom 404 page with navigation
- **AuthCallback** - OAuth redirect handler

## 🏗️ Project Structure

```
frontend/
├── src/
│   ├── components/              # Reusable components
│   │   ├── ChatWindow.tsx      # Main chat display
│   │   ├── Composer.tsx        # Message input
│   │   └── MessageBubble.tsx   # Message rendering
│   ├── pages/                   # Page components
│   │   ├── Chat.tsx            # Main chat page
│   │   ├── Login.tsx           # Login page
│   │   ├── AuthCallback.tsx    # OAuth callback handler
│   │   └── NotFound.tsx        # 404 page
│   ├── services/                # API clients
│   │   ├── api.ts              # Base API client
│   │   ├── auth.ts             # Authentication service
│   │   ├── chat.ts             # Chat service
│   │   └── history.ts          # History service (localStorage)
│   ├── hooks/                   # Custom React hooks
│   │   └── useAuth.tsx         # Authentication hook
│   ├── types/                   # TypeScript types
│   │   └── index.ts            # Shared type definitions
│   ├── lib/                     # Utilities
│   ├── assets/                  # Static assets
│   ├── App.tsx                  # Root component
│   ├── main.tsx                 # Entry point
│   └── index.css               # Global styles
├── public/                      # Public assets
├── index.html                   # HTML template
├── package.json                 # Dependencies
├── tsconfig.json               # TypeScript config
├── vite.config.ts              # Vite config
├── tailwind.config.js          # Tailwind config
├── postcss.config.js           # PostCSS config
├── eslint.config.js            # ESLint config
└── README.md                   # This file
```

## 🎨 Tech Stack

- **React 18.3** - Modern React with hooks and concurrent features
- **TypeScript 5.6** - Type safety and better DX
- **Vite 7.1** - Lightning-fast build tool and dev server
- **Tailwind CSS 3.4** - Utility-first CSS framework
- **React Router 7.2** - Client-side routing
- **Axios** - HTTP client for API calls

## 📡 API Integration

### Services

#### Authentication Service (`services/auth.ts`)
```typescript
// Login with Google
authService.loginWithGoogle()

// Connect HubSpot
authService.connectHubSpot()

// Get current session
const user = await authService.getSession()

// Logout
await authService.logout()
```

#### Chat Service (`services/chat.ts`)
```typescript
// Stream chat messages
await chatService.streamMessage(
  message,
  conversationId,
  onChunk,
  onError
)
```

#### History Service (`services/history.ts`)
```typescript
// Save conversation
historyService.saveConversation(conversation)

// Get all conversations
const conversations = historyService.getAllConversations()

// Search conversations
const results = historyService.searchConversations(query)
```

### API Client

Base client configuration in `services/api.ts`:
- Automatic base URL detection
- Request/response interceptors
- Error handling
- TypeScript types

## 🎯 Key Components

### Chat Page (`pages/Chat.tsx`)

Main application page with:
- User authentication check
- Chat/History tab navigation
- Message list management
- Streaming response handling
- Error handling and display

### ChatWindow (`components/ChatWindow.tsx`)

Displays messages and example prompts:
- Scrollable message list
- Example prompt cards
- Empty state with suggestions
- Auto-scroll to latest message

### Composer (`components/Composer.tsx`)

Message input component:
- Text input with auto-resize
- Send button with loading state
- Future features (disabled with tooltips):
  - File uploads
  - Voice input
  - Video messages

### Authentication Hook (`hooks/useAuth.tsx`)

Manages authentication state:
- User session loading
- Auto-refresh on mount
- Logout functionality
- HubSpot connection
- Global auth state

## 🎨 Styling

### Tailwind CSS

Utility-first approach with:
- Responsive breakpoints (`sm:`, `md:`, `lg:`, `xl:`)
- Custom color palette
- Hover and active states
- Transitions and animations

### Responsive Design

Mobile-first breakpoints:
- `sm`: 640px (small tablets)
- `md`: 768px (tablets)
- `lg`: 1024px (desktops)
- `xl`: 1280px (large desktops)

Example usage:
```tsx
<div className="px-3 sm:px-6 py-2 sm:py-4">
  <h1 className="text-lg sm:text-xl">Title</h1>
</div>
```

## 🧪 Testing

```bash
# Run tests (when implemented)
npm test

# Run tests in watch mode
npm run test:watch

# Generate coverage report
npm run test:coverage
```

## 🏗️ Build & Deployment

### Development Build

```bash
npm run dev
```

Features:
- Hot Module Replacement (HMR)
- Fast refresh
- Source maps
- Dev server on port 5173

### Production Build

```bash
npm run build
```

Output:
- Optimized bundle in `dist/`
- Minified JS and CSS
- Asset hashing for cache busting
- Source maps (optional)

Current build size: **~336 KB** (gzipped: ~109 KB)

### Preview Production Build

```bash
npm run preview
```

Test the production build locally before deployment.

### Deployment Options

#### Static Hosting (Vercel, Netlify, etc.)

```bash
# Build
npm run build

# Deploy dist/ folder to your hosting provider
```

Configure these settings:
- Build command: `npm run build`
- Output directory: `dist`
- Install command: `npm install`

#### Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (optional)
    location /api {
        proxy_pass http://backend:8000;
    }
}
```

#### Docker

```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🐛 Troubleshooting

### Common Issues

**Backend connection errors**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Verify CORS settings in backend
# Check browser console for errors
```

**Build errors**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

**TypeScript errors**
```bash
# Check TypeScript version
npx tsc --version

# Run type check
npm run type-check
```

**Styling issues**
```bash
# Rebuild Tailwind
npm run build

# Check Tailwind config
npx tailwindcss -i ./src/index.css -o ./dist/output.css
```

## 🔒 Security

- **XSS Protection** - React's built-in escaping
- **CSRF Protection** - SameSite cookies
- **Content Security Policy** - Restrictive CSP headers
- **Secure Cookies** - httpOnly, secure flags
- **No Sensitive Data** - Never store tokens in localStorage

## 📚 Resources

- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [React Router](https://reactrouter.com/)

## 🤝 Contributing

1. Follow existing code style
2. Use TypeScript strict mode
3. Add PropTypes or TypeScript interfaces
4. Write responsive, accessible components
5. Test on multiple screen sizes
6. Update documentation

## 📝 License

This project is private and proprietary.

---

**Built with React, TypeScript, and Tailwind CSS** ⚛️

      // Remove tseslint.configs.recommended and replace with this

## Prerequisites      tseslint.configs.recommendedTypeChecked,

      // Alternatively, use this for stricter rules

- Node.js 18+ and npm      tseslint.configs.strictTypeChecked,

- Backend server running on `http://localhost:8000`      // Optionally, add this for stylistic rules

      tseslint.configs.stylisticTypeChecked,

## Installation

      // Other configs...

```bash    ],

npm install    languageOptions: {

cp .env.example .env      parserOptions: {

```        project: ['./tsconfig.node.json', './tsconfig.app.json'],

        tsconfigRootDir: import.meta.dirname,

## Development      },

      // other options...

```bash    },

npm run dev  # Start dev server at http://localhost:5173  },

```])

```

## Build

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```bash

npm run build     # Production build```js

npm run preview   # Preview production build// eslint.config.js

```import reactX from 'eslint-plugin-react-x'

import reactDom from 'eslint-plugin-react-dom'

## Project Structure

export default defineConfig([

```  globalIgnores(['dist']),

src/  {

├── components/       # Reusable UI components    files: ['**/*.{ts,tsx}'],

├── pages/           # Page components      extends: [

├── services/        # API services      // Other configs...

├── hooks/           # Custom React hooks      // Enable lint rules for React

├── types/           # TypeScript types      reactX.configs['recommended-typescript'],

└── lib/             # Utility functions      // Enable lint rules for React DOM

```      reactDom.configs.recommended,

    ],

## Environment Variables    languageOptions: {

      parserOptions: {

- `VITE_API_BASE_URL` - Backend API URL (default: `http://localhost:8000`)        project: ['./tsconfig.node.json', './tsconfig.app.json'],

        tsconfigRootDir: import.meta.dirname,

## Security      },

      // other options...

- HttpOnly cookies for authentication    },

- DOMPurify for XSS protection  },

- CSRF protection via custom headers])

- No sensitive data in localStorage```

