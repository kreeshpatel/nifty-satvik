import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft } from 'lucide-react';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';

const API = process.env.REACT_APP_API_URL ?? '';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get('token') || '';

  const [pw1, setPw1] = useState('');
  const [pw2, setPw2] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (pw1 !== pw2) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: pw1 }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `Request failed (${res.status})`);
      }
      toast.success('Password updated. Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err.message || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-6"
        style={{ background: 'var(--surface-0)', color: 'var(--text-1)' }}
      >
        <div className="text-center max-w-md">
          <p style={{ fontSize: 15, marginBottom: 16 }}>
            This reset link is missing or malformed. Request a new one to continue.
          </p>
          <Link
            to="/forgot-password"
            style={{ color: 'var(--brand)', fontWeight: 600, fontSize: 14 }}
          >
            Request a new link
          </Link>
        </div>
      </div>
    );
  }

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
          Choose a new password
        </h1>
        <p className="mb-8" style={{ fontSize: 13, color: 'var(--text-3)' }}>
          Minimum 12 characters. Include at least 3 of: lowercase, uppercase, digit, symbol.
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            type="password"
            required
            autoComplete="new-password"
            placeholder="New password"
            value={pw1}
            onChange={(e) => setPw1(e.target.value)}
            className="h-12"
            style={{
              background: 'var(--surface-1)',
              border: '1px solid var(--edge-1)',
              color: 'var(--text-1)',
              borderRadius: 'var(--r-chip)',
              fontSize: 14,
            }}
          />
          <Input
            type="password"
            required
            autoComplete="new-password"
            placeholder="Confirm new password"
            value={pw2}
            onChange={(e) => setPw2(e.target.value)}
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
                Updating…
              </>
            ) : (
              'Set new password'
            )}
          </button>
        </form>
      </motion.div>
    </div>
  );
}
