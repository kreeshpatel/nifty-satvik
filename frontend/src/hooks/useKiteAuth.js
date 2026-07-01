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
      setIsLoggedIn(status.logged_in || false);
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
