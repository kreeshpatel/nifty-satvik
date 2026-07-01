import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { Input } from '@/components/ui/input';

const API = process.env.REACT_APP_API_URL ?? '';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${res.status})`);
      }
      setSubmitted(true);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-6"
      style={{ background: 'var(--surface-0)', color: 'var(--text-1)' }}
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 mb-6 text-sm transition-opacity hover:opacity-80"
          style={{ color: 'var(--text-3)' }}
        >
          <ArrowLeft size={14} /> Back to sign in
        </Link>

        <h1
          className="mb-2"
          style={{ fontSize: 28, fontWeight: 600, letterSpacing: '-0.02em' }}
        >
          Reset your password
        </h1>
        <p className="mb-8" style={{ fontSize: 14, color: 'var(--text-3)' }}>
          Enter the email associated with your account. If it’s registered, we’ll send a reset link.
        </p>

        {submitted ? (
          <div
            className="flex items-start gap-3 px-4 py-3.5"
            style={{
              background: 'oklch(70% 0.13 145 / 0.08)',
              border: '1px solid oklch(70% 0.13 145 / 0.25)',
              borderRadius: 'var(--r-chip)',
            }}
          >
            <CheckCircle2 size={18} style={{ color: 'var(--bull)', marginTop: 2 }} />
            <div style={{ fontSize: 13.5 }}>
              If that email is registered, we’ve sent a reset link. Check your inbox — the link expires in 30 minutes.
            </div>
          </div>
        ) : (
          <form onSubmit={onSubmit} className="space-y-4">
            <Input
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-12"
              style={{
                background: 'var(--surface-1)',
                border: '1px solid var(--edge-1)',
                color: 'var(--text-1)',
                borderRadius: 'var(--r-chip)',
                fontSize: 14,
              }}
            />

            {error && (
              <div
                className="px-3.5 py-2.5"
                style={{
                  background: 'oklch(66% 0.21 25 / 0.08)',
                  border: '1px solid oklch(66% 0.21 25 / 0.25)',
                  borderRadius: 'var(--r-chip)',
                  fontSize: 12,
                  color: 'var(--bear)',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 inline-flex items-center justify-center gap-2 disabled:opacity-70"
              style={{
                background: 'var(--brand)',
                color: 'var(--brand-fg)',
                borderRadius: 'var(--r-chip)',
                border: 'none',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Sending…
                </>
              ) : (
                'Send reset link'
              )}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
}
