import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refetch } = useAuth();
  const error = searchParams.get('error');

  useEffect(() => {
    const handleCallback = async () => {
      if (error) {
        console.error('OAuth error:', error);
        navigate('/login');
        return;
      }

      try {
        await refetch();
        navigate('/');
      } catch (err) {
        console.error('Failed to refresh user session:', err);
        navigate('/login');
      }
    };

    handleCallback();
  }, [error, navigate, refetch]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <p className="text-gray-600">
          {error ? 'Authentication failed. Redirecting...' : 'Completing authentication...'}
        </p>
      </div>
    </div>
  );
}
