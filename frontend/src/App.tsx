import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import Login from './pages/Login';
import Chat from './pages/Chat';
import AuthCallback from './pages/AuthCallback';
import NotFound from './pages/NotFound';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/success" element={<AuthCallback />} />
          <Route path="/auth/error" element={<AuthCallback />} />
          <Route path="/auth/hubspot/success" element={<AuthCallback />} />
          <Route path="/auth/hubspot/error" element={<AuthCallback />} />
          <Route path="/" element={<Chat />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
