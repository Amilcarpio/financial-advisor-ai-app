# Financial Advisor AI - Frontend# React + TypeScript + Vite



React + TypeScript + Vite + Tailwind CSS frontend for the Financial Advisor AI application.This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.



## FeaturesCurrently, two official plugins are available:



- 🔐 Google OAuth authentication- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh

- 💬 ChatGPT-like chat interface with streaming responses- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

- 🤖 AI agent integration with tool calling visualization

- 📧 Gmail and HubSpot CRM integration## React Compiler

- 📅 Calendar management

- 🎨 Responsive design matching provided UI mockupsThe React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

- 🔒 Security-first architecture (XSS protection, CSP, sanitization)

## Expanding the ESLint configuration

## Tech Stack

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

- **React 18** - UI library

- **TypeScript** - Type safety```js

- **Vite** - Build tool and dev serverexport default defineConfig([

- **Tailwind CSS** - Utility-first CSS  globalIgnores(['dist']),

- **Axios** - HTTP client  {

- **SWR** - Data fetching and caching    files: ['**/*.{ts,tsx}'],

- **DOMPurify** - XSS protection    extends: [

- **React Router** - Client-side routing      // Other configs...

- **date-fns** - Date utilities

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

