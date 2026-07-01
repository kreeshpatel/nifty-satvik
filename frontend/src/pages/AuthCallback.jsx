/**
 * AuthCallback — handles the Kite OAuth redirect.
 *
 * Why this file exists:
 *   The Zerodha developer console is configured to redirect to
 *   `<origin>/auth/callback?request_token=xyz&action=login&status=success`
 *   after successful Kite OAuth. Before this file existed, that route was
 *   not declared in App.js, so React Router fell through to the catch-all
 *   `<Navigate to="/" replace />` and the user landed on the public landing
 *   page with the request_token silently dropped from the URL — Kite never
 *   got connected.
 *
 *   This component lives OUTSIDE `ProtectedAppLayout` so the chrome (sidebar,
 *   header) doesn't briefly flash during the ~500ms exchange. It does need
 *   the NiftyQuant session cookie to be present, since `kiteExchangeToken`
 *   hits a backend endpoint guarded by `get_current_user`. If that's missing
 *   we surface a clear "sign in first" toast and redirect to /login.
 *
 * Flow:
 *   1. Read request_token / status / action from search params
 *   2. If status !== 'success' or no token → toast error, navigate to /dashboard
 *   3. Call kiteExchangeToken(request_token)
 *   4. On success → toast "Kite connected as <user_id>", navigate to /dashboard
 *      (ProtectedAppLayout's mount effect will then refresh KiteContext via
 *      kiteSessionStatus() — no explicit context update needed here)
 *   5. On failure → toast surfaces backend error message, navigate to /dashboard
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { kiteExchangeToken } from '@/services/api';

export default function AuthCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [phase, setPhase] = useState('exchanging');   // 'exchanging' | 'redirecting'

  // useRef guard — prevents double-fire of kiteExchangeToken in React StrictMode
  // (effects run twice in dev). Kite request_tokens are single-use, so the
  // second call would always fail with "Token expired or invalid" and toast
  // confusingly even though the first call succeeded.
  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    const requestToken = searchParams.get('request_token');
    const status = searchParams.get('status');
    const action = searchParams.get('action');

    // Sanity check — Kite always sends action=login for OAuth replies.
    if (!requestToken || status !== 'success' || action !== 'login') {
      toast.error('Kite login was cancelled or failed', {
        description: status === 'failure'
          ? 'Zerodha rejected the connection. Try again.'
          : 'Missing or invalid response from Kite.',
      });
      navigate('/dashboard', { replace: true });
      return;
    }

    kiteExchangeToken(requestToken)
      .then((res) => {
        // Backend returns { status: 'success', user_id, user_name } or an
        // error shape like { detail: '...' } / { error: '...' }.
        if (res?.status === 'success' || res?.user_id) {
          toast.success(`Kite connected${res?.user_id ? ` as ${res.user_id}` : ''}`, {
            description: 'Live holdings, orders, and trading are now active.',
          });
          setPhase('redirecting');
          navigate('/dashboard', { replace: true });
          return;
        }
        // Non-error HTTP but the body indicates failure.
        const reason = res?.detail || res?.error || res?.message || 'Unknown error';
        // 401 from the backend (no NQ session cookie) typically means the user
        // wasn't logged in to NiftyQuant when they came back from Kite.
        const looksAuth = /unauthor|401|sign in|login/i.test(reason);
        toast.error('Kite connection failed', {
          description: looksAuth
            ? 'Sign in to NiftyQuant first, then click Connect Kite again.'
            : `Kite: ${reason}`,
        });
        setPhase('redirecting');
        navigate(looksAuth ? '/login' : '/dashboard', { replace: true });
      })
      .catch((err) => {
        toast.error('Kite connection failed', {
          description: err?.message
            ? `Kite: ${err.message}`
            : 'Network error during token exchange. Try again.',
        });
        setPhase('redirecting');
        navigate('/dashboard', { replace: true });
      });
  }, [navigate, searchParams]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'var(--surface-0, #000)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
        zIndex: 1,
      }}
      aria-busy="true"
      aria-live="polite"
    >
      <div
        style={{
          width: 36,
          height: 36,
          border: '2px solid var(--edge-1, rgba(255,255,255,0.08))',
          borderTopColor: 'var(--brand, #4F8CFF)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <div style={{ textAlign: 'center', maxWidth: 320 }}>
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 16,
            color: 'var(--text-1, #FFF)',
            marginBottom: 6,
          }}
        >
          {phase === 'redirecting' ? 'Redirecting…' : 'Connecting Kite…'}
        </div>
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 13,
            color: 'var(--text-3, rgba(255,255,255,0.48))',
          }}
        >
          {phase === 'redirecting'
            ? 'Taking you to your dashboard.'
            : 'Exchanging request token with Zerodha. This usually takes under a second.'}
        </div>
      </div>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @media (prefers-reduced-motion: reduce) {
          [aria-busy="true"] > div:first-child { animation: none !important; }
        }
      `}</style>
    </div>
  );
}
