import React from 'react';
import { getKiteLoginUrl } from '@/services/api';
import { LogIn, CheckCircle } from 'lucide-react';

// Your Kite API key (replace with actual key or get from env)
const KITE_API_KEY = import.meta.env.VITE_KITE_API_KEY || 'your_kite_api_key';

export const KiteAuthButton = ({ isLoggedIn, userId, onConnect }) => {
  const handleLogin = () => {
    const loginUrl = getKiteLoginUrl(KITE_API_KEY);
    window.location.href = loginUrl;
  };

  if (isLoggedIn) {
    return (
      <div
        className="flex items-center gap-2 px-4 py-2 rounded-xl"
        style={{
          background: 'rgba(34, 197, 94, 0.15)',
          border: '1px solid rgba(34, 197, 94, 0.3)',
        }}
      >
        <CheckCircle className="h-4 w-4" style={{ color: '#22C55E' }} />
        <span className="text-sm font-medium" style={{ color: '#22C55E' }}>
          Kite Connected · {userId}
        </span>
      </div>
    );
  }

  return (
    <button
      onClick={onConnect || handleLogin}
      className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200"
      style={{ background: 'linear-gradient(135deg, #2C5BFF 0%, #4F8CFF 50%, #7B5BFF 100%)', color: '#fff', boxShadow: '0 6px 18px rgba(79,140,255,0.40)' }}
      onMouseEnter={(e) => {
        e.currentTarget.style.filter = 'brightness(1.08)';
        e.currentTarget.style.transform = 'translateY(-1px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.filter = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      <LogIn className="h-4 w-4" />
      Connect to Kite
    </button>
  );
};
