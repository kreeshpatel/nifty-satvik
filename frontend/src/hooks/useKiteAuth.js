import { useState, useEffect } from 'react';
import { kiteSessionStatus, handleKiteCallback } from '@/services/api';

/**
 * Custom hook for Kite authentication state
 * @returns {Object} { isLoggedIn, userId, checkSession, handleCallback }
 */
export const useKiteAuth = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check session status
  const checkSession = async () => {
    try {
      const status = await kiteSessionStatus();
      // Backend GET /api/kite/session/status returns {connected, user_id} (NOT logged_in);
      // read `connected` first so this reports the real state if ever wired into the live app.
      setIsLoggedIn(status.connected ?? status.logged_in ?? false);
      setUserId(status.user_id || null);
    } catch (error) {
      console.error('Failed to check Kite session:', error);
      setIsLoggedIn(false);
      setUserId(null);
    } finally {
      setLoading(false);
    }
  };

  // Handle Kite callback after redirect
  const handleCallback = async () => {
    try {
      const session = await handleKiteCallback();
      if (session) {
        setIsLoggedIn(true);
        setUserId(session.user_id);
        return session;
      }
    } catch (error) {
      console.error('Kite callback failed:', error);
      throw error;
    }
  };

  // Check session on mount
  useEffect(() => {
    checkSession();
  }, []);

  return {
    isLoggedIn,
    userId,
    loading,
    checkSession,
    handleCallback,
  };
};

export default useKiteAuth;
