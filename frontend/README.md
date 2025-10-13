# Frontend - Financial Advisor AI# Financial Advisor AI - Frontend



React-based frontend application providing an intuitive interface for AI-powered financial advisory automation.React + TypeScript + Vite frontend for the Financial Advisor AI application with a modern, responsive chat interface.



## Overview## 🚀 Quick Start



The frontend is a modern single-page application built with React and TypeScript, featuring:```bash

- Interactive chat interface with streaming responses# Install dependencies

- Real-time data synchronizationnpm install

- OAuth authentication flow

- Memory rules management# Start development server

- Responsive design for all devicesnpm run dev



## Technology Stack# Build for production

npm run build

- **React 18**: Modern React with hooks and concurrent features

- **TypeScript**: Type-safe JavaScript# Preview production build

- **Vite**: Next-generation frontend build toolnpm run preview

- **TanStack Query**: Powerful data fetching and caching```

- **Tailwind CSS**: Utility-first CSS framework

- **React Router v6**: Client-side routingThe app will be available at `http://localhost:5173`

- **Lucide React**: Beautiful icon library

## 📋 Prerequisites

## Project Structure

- Node.js 18+

```- npm or yarn

frontend/- Backend API running at `http://localhost:8000` (or configured via VITE_API_URL)

├── src/

│   ├── components/       # Reusable React components## 🔧 Configuration

│   │   ├── AuthGuard.tsx

│   │   ├── ChatInput.tsx### Environment Variables

│   │   ├── ChatMessage.tsx

│   │   └── ...Create a `.env.local` file in the frontend directory (optional):

│   ├── lib/             # Utilities and configurations

│   │   ├── api.ts       # API client```bash

│   │   ├── auth.ts      # Authentication utilities# API endpoint (defaults to http://localhost:8000)

│   │   └── utils.ts     # Helper functionsVITE_API_URL=http://localhost:8000

│   ├── pages/           # Page components

│   │   ├── Chat.tsx# Enable debug mode

│   │   ├── Home.tsxVITE_DEBUG=true

│   │   ├── Login.tsx```

│   │   └── Settings.tsx

│   ├── App.tsx          # Main app componentThe app automatically detects the backend URL, so configuration is only needed for custom setups.

│   ├── main.tsx         # Application entry point

│   └── index.css        # Global styles## ✨ Features

├── public/              # Static assets

├── index.html           # HTML template### Authentication

├── vite.config.ts       # Vite configuration- 🔐 **Google OAuth Integration** - Secure login with Google accounts

├── tailwind.config.js   # Tailwind CSS configuration- 🍪 **Session Management** - httpOnly cookies for security

├── tsconfig.json        # TypeScript configuration- 👤 **User Profile** - Display name and avatar from Google

└── package.json         # Dependencies and scripts- 🔗 **HubSpot Connection** - Optional CRM integration

```

### Chat Interface

## Prerequisites- 💬 **Real-time Streaming** - Live AI responses with typing indicators

- 🤖 **Function Calling** - Visual feedback when AI uses tools

- Node.js 18 or higher- 📝 **Example Prompts** - Quick-start suggestions for users

- npm or yarn package manager- 💾 **Chat History** - Save and load previous conversations (coming soon)

- Backend API running (see backend/README.md)- 📱 **Mobile Responsive** - Works perfectly on all screen sizes



## Environment Configuration### UI/UX

- 🎨 **Modern Design** - Clean, professional interface

Create a `.env` file in the frontend directory:- 🌙 **Smooth Animations** - Hover effects and transitions

- ♿ **Accessibility** - Keyboard navigation and ARIA labels

```env- 🎯 **Smart Tooltips** - Helpful hints for disabled features

VITE_API_URL=http://localhost:8000- 🔄 **Tab Navigation** - Switch between Chat and History views

VITE_APP_NAME=Financial Advisor AI

```### Components

- **ChatWindow** - Message display with streaming support

For production deployment to GitHub Pages:- **Composer** - Message input with future file upload support

- **MessageBubble** - Individual message rendering

```env- **NotFound** - Custom 404 page with navigation

VITE_API_URL=https://your-backend-domain.com- **AuthCallback** - OAuth redirect handler

VITE_APP_NAME=Financial Advisor AI

```## 🏗️ Project Structure



## Installation```

frontend/

```bash├── src/

# Install dependencies│   ├── components/              # Reusable components

npm install│   │   ├── ChatWindow.tsx      # Main chat display

│   │   ├── Composer.tsx        # Message input

# Start development server│   │   └── MessageBubble.tsx   # Message rendering

npm run dev│   ├── pages/                   # Page components

│   │   ├── Chat.tsx            # Main chat page

# Build for production│   │   ├── Login.tsx           # Login page

npm run build│   │   ├── AuthCallback.tsx    # OAuth callback handler

│   │   └── NotFound.tsx        # 404 page

# Preview production build│   ├── services/                # API clients

npm run preview│   │   ├── api.ts              # Base API client

```│   │   ├── auth.ts             # Authentication service

│   │   ├── chat.ts             # Chat service

## Development│   │   └── history.ts          # History service (localStorage)

│   ├── hooks/                   # Custom React hooks

### Development Server│   │   └── useAuth.tsx         # Authentication hook

│   ├── types/                   # TypeScript types

```bash│   │   └── index.ts            # Shared type definitions

npm run dev│   ├── lib/                     # Utilities

```│   ├── assets/                  # Static assets

│   ├── App.tsx                  # Root component

The application will be available at http://localhost:5173│   ├── main.tsx                 # Entry point

│   └── index.css               # Global styles

### Code Quality├── public/                      # Public assets

├── index.html                   # HTML template

```bash├── package.json                 # Dependencies

# Run ESLint├── tsconfig.json               # TypeScript config

npm run lint├── vite.config.ts              # Vite config

├── tailwind.config.js          # Tailwind config

# Type check├── postcss.config.js           # PostCSS config

npm run type-check├── eslint.config.js            # ESLint config

└── README.md                   # This file

# Format code```

npm run format

```## 🎨 Tech Stack



### Component Development- **React 18.3** - Modern React with hooks and concurrent features

- **TypeScript 5.6** - Type safety and better DX

Components follow these conventions:- **Vite 7.1** - Lightning-fast build tool and dev server

- Functional components with TypeScript- **Tailwind CSS 3.4** - Utility-first CSS framework

- Props interfaces defined at the top- **React Router 7.2** - Client-side routing

- Hooks used for state management- **Axios** - HTTP client for API calls

- TanStack Query for server state

## 📡 API Integration

Example component:

### Services

```typescript

interface ChatMessageProps {#### Authentication Service (`services/auth.ts`)

  message: string;```typescript

  sender: 'user' | 'assistant';// Login with Google

  timestamp: Date;authService.loginWithGoogle()

}

// Connect HubSpot

export function ChatMessage({ message, sender, timestamp }: ChatMessageProps) {authService.connectHubSpot()

  return (

    <div className={`message ${sender}`}>// Get current session

      <p>{message}</p>const user = await authService.getSession()

      <span>{timestamp.toLocaleString()}</span>

    </div>// Logout

  );await authService.logout()

}```

```

#### Chat Service (`services/chat.ts`)

## API Integration```typescript

// Stream chat messages

The application uses a centralized API client (`src/lib/api.ts`) for all backend communication:await chatService.streamMessage(

  message,

```typescript  conversationId,

import { apiClient } from '@/lib/api';  onChunk,

  onError

// Example usage)

const { data, isLoading, error } = useQuery({```

  queryKey: ['messages'],

  queryFn: () => apiClient.get('/api/chat/messages'),#### History Service (`services/history.ts`)

});```typescript

```// Save conversation

historyService.saveConversation(conversation)

### Authentication Flow

// Get all conversations

1. User clicks "Login with Google"const conversations = historyService.getAllConversations()

2. Frontend redirects to backend OAuth endpoint

3. Backend handles Google OAuth flow// Search conversations

4. Backend redirects back with JWT tokenconst results = historyService.searchConversations(query)

5. Frontend stores token and redirects to chat```



## Building for Production### API Client



### Standard BuildBase client configuration in `services/api.ts`:

- Automatic base URL detection

```bash- Request/response interceptors

npm run build- Error handling

```- TypeScript types



Output will be in the `dist/` directory.## 🎯 Key Components



### GitHub Pages Deployment### Chat Page (`pages/Chat.tsx`)



The application is configured for static deployment to GitHub Pages.Main application page with:

- User authentication check

#### Configuration- Chat/History tab navigation

- Message list management

Update `vite.config.ts`:- Streaming response handling

- Error handling and display

```typescript

export default defineConfig({### ChatWindow (`components/ChatWindow.tsx`)

  base: '/financial-advisor-ai-app/',  // Your repository name

  // ... other configDisplays messages and example prompts:

});- Scrollable message list

```- Example prompt cards

- Empty state with suggestions

Update `package.json`:- Auto-scroll to latest message



```json### Composer (`components/Composer.tsx`)

{

  "scripts": {Message input component:

    "deploy": "npm run build && gh-pages -d dist"- Text input with auto-resize

  }- Send button with loading state

}- Future features (disabled with tooltips):

```  - File uploads

  - Voice input

#### Deploy  - Video messages



```bash### Authentication Hook (`hooks/useAuth.tsx`)

# Install gh-pages

npm install --save-dev gh-pagesManages authentication state:

- User session loading

# Build and deploy- Auto-refresh on mount

npm run deploy- Logout functionality

```- HubSpot connection

- Global auth state

The site will be available at:

`https://yourusername.github.io/financial-advisor-ai-app/`## 🎨 Styling



#### GitHub Repository Settings### Tailwind CSS



1. Go to repository Settings > PagesUtility-first approach with:

2. Set Source to "gh-pages" branch- Responsive breakpoints (`sm:`, `md:`, `lg:`, `xl:`)

3. Save settings- Custom color palette

4. Wait for GitHub Actions to complete- Hover and active states

- Transitions and animations

## Styling

### Responsive Design

### Tailwind CSS

Mobile-first breakpoints:

The application uses Tailwind CSS for styling:- `sm`: 640px (small tablets)

- `md`: 768px (tablets)

```tsx- `lg`: 1024px (desktops)

<button className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">- `xl`: 1280px (large desktops)

  Click Me

</button>Example usage:

``````tsx

<div className="px-3 sm:px-6 py-2 sm:py-4">

### Custom Styles  <h1 className="text-lg sm:text-xl">Title</h1>

</div>

Global styles are in `src/index.css`. Component-specific styles use Tailwind classes.```



### Responsive Design## 🧪 Testing



All components are mobile-first responsive:```bash

# Run tests (when implemented)

```tsxnpm test

<div className="flex flex-col md:flex-row lg:grid-cols-3">

  {/* Content adapts to screen size */}# Run tests in watch mode

</div>npm run test:watch

```

# Generate coverage report

## State Managementnpm run test:coverage

```

### React Query (TanStack Query)

## 🏗️ Build & Deployment

Server state is managed with React Query:

### Development Build

```typescript

const { data, isLoading, error, refetch } = useQuery({```bash

  queryKey: ['contacts'],npm run dev

  queryFn: () => apiClient.get('/api/contacts'),```

  staleTime: 5 * 60 * 1000, // 5 minutes

});Features:

```- Hot Module Replacement (HMR)

- Fast refresh

### Local State- Source maps

- Dev server on port 5173

Component-level state uses React hooks:

### Production Build

```typescript

const [message, setMessage] = useState('');```bash

const [isOpen, setIsOpen] = useState(false);npm run build

``````



## RoutingOutput:

- Optimized bundle in `dist/`

React Router v6 handles navigation:- Minified JS and CSS

- Asset hashing for cache busting

```typescript- Source maps (optional)

import { BrowserRouter, Routes, Route } from 'react-router-dom';

Current build size: **~336 KB** (gzipped: ~109 KB)

<BrowserRouter>

  <Routes>### Preview Production Build

    <Route path="/" element={<Home />} />

    <Route path="/chat" element={<Chat />} />```bash

    <Route path="/settings" element={<Settings />} />npm run preview

  </Routes>```

</BrowserRouter>

```Test the production build locally before deployment.



## Testing### Deployment Options



```bash#### Static Hosting (Vercel, Netlify, etc.)

# Run tests

npm test```bash

# Build

# Run tests with coveragenpm run build

npm run test:coverage

# Deploy dist/ folder to your hosting provider

# Run tests in watch mode```

npm run test:watch

```Configure these settings:

- Build command: `npm run build`

## Performance Optimization- Output directory: `dist`

- Install command: `npm install`

- Code splitting with React.lazy()

- Image optimization#### Nginx

- Lazy loading of components

- Memoization with useMemo and useCallback```nginx

- Virtual scrolling for long listsserver {

    listen 80;

## Browser Support    server_name yourdomain.com;

    root /path/to/dist;

- Chrome (latest 2 versions)    index index.html;

- Firefox (latest 2 versions)

- Safari (latest 2 versions)    location / {

- Edge (latest 2 versions)        try_files $uri $uri/ /index.html;

    }

## Troubleshooting

    # API proxy (optional)

### Common Issues    location /api {

        proxy_pass http://backend:8000;

**Build fails with TypeScript errors:**    }

```bash}

# Clear node_modules and reinstall```

rm -rf node_modules package-lock.json

npm install#### Docker

```

```dockerfile

**API requests fail:**FROM node:18-alpine AS build

```bashWORKDIR /app

# Check VITE_API_URL in .envCOPY package*.json ./

# Ensure backend is runningRUN npm ci

# Check browser console for CORS errorsCOPY . .

```RUN npm run build



**Styles not updating:**FROM nginx:alpine

```bashCOPY --from=build /app/dist /usr/share/nginx/html

# Clear Vite cacheCOPY nginx.conf /etc/nginx/conf.d/default.conf

rm -rf node_modules/.viteEXPOSE 80

npm run devCMD ["nginx", "-g", "daemon off;"]

``````



**GitHub Pages 404 errors:**## 🐛 Troubleshooting

```bash

# Ensure base path in vite.config.ts matches repository name### Common Issues

# Check GitHub Pages settings

# Wait for GitHub Actions to complete**Backend connection errors**

``````bash

# Check backend is running

## Deployment Checklistcurl http://localhost:8000/api/health



- [ ] Update `.env` with production API URL# Verify CORS settings in backend

- [ ] Set correct `base` path in `vite.config.ts`# Check browser console for errors

- [ ] Run `npm run build` successfully```

- [ ] Test production build locally with `npm run preview`

- [ ] Configure CORS in backend for production domain**Build errors**

- [ ] Set up GitHub Pages settings```bash

- [ ] Deploy with `npm run deploy`# Clear node_modules and reinstall

- [ ] Verify deployment at GitHub Pages URLrm -rf node_modules package-lock.json

npm install

## Contributing

# Clear Vite cache

1. Follow React and TypeScript best practicesrm -rf node_modules/.vite

2. Use functional components with hooks```

3. Write self-documenting code with clear prop types

4. Keep components small and focused**TypeScript errors**

5. Use Tailwind CSS for styling```bash

6. Add PropTypes or TypeScript interfaces# Check TypeScript version

7. Test new featuresnpx tsc --version



## License# Run type check

npm run type-check

Proprietary and confidential. Unauthorized copying or distribution is prohibited.```


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

