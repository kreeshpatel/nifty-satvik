/**
 * Sign in — design v5 "Ledger" (docs/DESIGN_BRIEF_V5.md).
 *
 * A focused, security-first page: no performance figures (the previous page showed un-caveated
 * fallback stats that contradicted the landing's reviewed numbers), no decorative animation.
 * Auth behaviour is unchanged: AuthContext.login → optional MFA step → AuthContext.loginMfa.
 */
import { useState, useContext, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Eye, EyeOff, Loader2, Lock, ShieldCheck, KeyRound } from 'lucide-react';
import { AuthContext } from '@/context/AuthContext';
import BrandMark from '@/components/brand/BrandMark';
import '@/styles/auth-v5.css';

export default function Login() {
  const { login, loginMfa } = useContext(AuthContext);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [caps, setCaps] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  // MFA: set after a successful password step when the user has 2FA enabled.
  const [mfaPendingToken, setMfaPendingToken] = useState(null);
  const [mfaCode, setMfaCode] = useState('');
  const codeRef = useRef(null);

  useEffect(() => { document.title = 'Sign in — Nifty Satvik'; }, []);
  useEffect(() => { if (mfaPendingToken) codeRef.current?.focus(); }, [mfaPendingToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);
    try {
      const result = await login(email.trim(), password);
      if (result?.mfaRequired) setMfaPendingToken(result.mfaPendingToken);
    } catch (err) {
      setError(err.message || 'Sign-in failed. Check your email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);
    try {
      await loginMfa(mfaPendingToken, mfaCode);
    } catch (err) {
      setError(err.message || 'That code did not work. Try the current one.');
      setMfaCode('');
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e) => setCaps(Boolean(e.getModifierState && e.getModifierState('CapsLock')));

  return (
    <div className="auth5">
      <aside className="auth5-side" aria-hidden="true">
        <Link to="/" className="auth5-brand" tabIndex={-1}>
          <BrandMark size={28} /> Nifty Satvik
        </Link>
        <div className="auth5-side-body">
          <p className="auth5-quote">Systematic swing research<br /><span>for the Nifty 500.</span></p>
          <ul className="auth5-points">
            <li><ShieldCheck size={16} />No broker connection. We never place an order or hold your capital.</li>
            <li><KeyRound size={16} />Two-factor authentication available for every account.</li>
            <li><Lock size={16} />Encrypted in transit; sessions expire and can be revoked.</li>
          </ul>
        </div>
        <p className="auth5-side-foot">Research and decision-support output, not investment advice.</p>
      </aside>

      <main className="auth5-main">
        <div className="auth5-top">
          <Link to="/" className="auth5-back"><ArrowLeft size={15} aria-hidden /> Home</Link>
          <Link to="/" className="auth5-brand auth5-brand-m"><BrandMark size={24} /> Nifty Satvik</Link>
        </div>

        <div className="auth5-card">
          <h1>{mfaPendingToken ? 'Two-step verification' : 'Sign in'}</h1>
          <p className="auth5-lede">
            {mfaPendingToken ? 'Enter the 6-digit code from your authenticator app.' : 'Welcome back. Use the email you were invited with.'}
          </p>

          <div className="auth5-error" role="alert" aria-live="assertive">{error && <span>{error}</span>}</div>

          {mfaPendingToken ? (
            <form onSubmit={handleMfaSubmit} noValidate>
              <label className="auth5-field">
                <span>Authentication code</span>
                <input
                  ref={codeRef}
                  id="mfa-code" name="code" type="text" inputMode="numeric" autoComplete="one-time-code"
                  maxLength={6} pattern="[0-9]{6}" required placeholder="000000"
                  className="auth5-input auth5-code"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  aria-invalid={Boolean(error)}
                />
              </label>
              <button type="submit" className="auth5-submit" disabled={loading || mfaCode.length !== 6}>
                {loading ? <><Loader2 size={16} className="auth5-spin" aria-hidden /> Verifying…</> : 'Verify and continue'}
              </button>
              <button type="button" className="auth5-link" onClick={() => { setMfaPendingToken(null); setMfaCode(''); setError(''); }}>
                Use a different account
              </button>
            </form>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              <label className="auth5-field">
                <span>Email</span>
                <input
                  id="email" name="email" type="email" autoComplete="username" inputMode="email" required autoFocus
                  spellCheck={false} autoCapitalize="none"
                  className="auth5-input" placeholder="you@example.com"
                  value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={Boolean(error)}
                />
              </label>
              <label className="auth5-field">
                <span className="auth5-field-row">
                  Password
                  <Link to="/forgot-password" className="auth5-forgot">Forgot password?</Link>
                </span>
                <span className="auth5-pw">
                  <input
                    id="password" name="password" type={show ? 'text' : 'password'} autoComplete="current-password" required
                    className="auth5-input" value={password}
                    onChange={(e) => setPassword(e.target.value)} onKeyUp={onKey} onKeyDown={onKey}
                    aria-invalid={Boolean(error)} aria-describedby={caps ? 'caps-hint' : undefined}
                  />
                  <button type="button" className="auth5-eye" onClick={() => setShow(!show)}
                    aria-label={show ? 'Hide password' : 'Show password'} aria-pressed={show}>
                    {show ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </span>
                {caps && <span id="caps-hint" className="auth5-hint">Caps Lock is on</span>}
              </label>
              <button type="submit" className="auth5-submit" disabled={loading || !email || !password}>
                {loading ? <><Loader2 size={16} className="auth5-spin" aria-hidden /> Signing in…</> : 'Sign in'}
              </button>
            </form>
          )}

          {!mfaPendingToken && (
            <p className="auth5-alt">New here? <Link to="/">Request access</Link> — Nifty Satvik is invite-only.</p>
          )}
        </div>

        <footer className="auth5-foot">
          <Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/disclaimer">Disclaimer</Link>
        </footer>
      </main>
    </div>
  );
}
