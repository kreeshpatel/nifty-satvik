/**
 * SettingsV2 — Settings page.
 *
 * Sections (tier-toned dots so the form-heavy page reads chromatically
 * instead of as a stack of muted-gray panels):
 *   1. Profile         — info tone, read-only (name, email, role) from /api/auth/me
 *   2. Security        — brand tone, opt-in TOTP MFA
 *                        warn when disconnected/expired)
 *   4. Notifications   — muted tone, email toggles (localStorage for now)
 *   5. Theme           — muted tone, locked-dark display
 *   6. Danger zone     — bear tone, sign-out as a text link
 */
import React, { useContext, useEffect, useState } from 'react';
import { LogOut, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { QRCodeSVG } from 'qrcode.react';
import { PageShell } from '@/components/shared/PageShell';
import { StatusChip } from '@/components/shared/StatusChip';
import { AuthContext } from '@/context/AuthContext';
import { fetchMfaStatus, mfaSetup, mfaVerify, mfaDisable } from '@/services/api';

const NOTIFICATION_PREFS_KEY = 'nq_notif_prefs';

export default function SettingsV2() {
  const { user, logout } = useContext(AuthContext);
  const [notifPrefs, setNotifPrefs] = useState({ signal_fired: true, stop_hit: true, daily_summary: false });
  const [activeTab, setActiveTab] = useState('account');

  useEffect(() => {
    try {
      const raw = localStorage.getItem(NOTIFICATION_PREFS_KEY);
      if (raw) setNotifPrefs({ ...notifPrefs, ...JSON.parse(raw) });
    } catch (_) {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateNotifPref = (key, value) => {
    const next = { ...notifPrefs, [key]: value };
    setNotifPrefs(next);
    try { localStorage.setItem(NOTIFICATION_PREFS_KEY, JSON.stringify(next)); } catch (_) {}
    toast.success('Preference saved');
  };

  return (
    <PageShell title="Settings" heroTone={null}>
      <div style={{ paddingTop: 24, paddingBottom: 24 }}>
        <h1 className="t-title-1" style={{ margin: 0, fontSize: 28, fontWeight: 600, color: 'var(--text-1)' }}>Settings</h1>
      </div>

      {/* 2-Col Layout: 200px sidebar | flex-1 form — stacks on mobile */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 22 }} className="settings-layout">

        {/* LEFT: Sidebar nav — horizontal scroll on mobile */}
        <nav className="settings-nav" style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[
            { id: 'account', label: 'Account' },
            { id: 'notifications', label: 'Notifications' },
            { id: 'risk', label: 'Risk caps' },
            { id: 'security', label: 'Security' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
              className="settings-tab-btn"
              style={{
                textAlign: 'left',
                padding: '10px 14px',
                background: activeTab === tab.id ? 'var(--brand-soft)' : 'transparent',
                color: activeTab === tab.id ? 'var(--text-1)' : 'var(--text-3)',
                border: activeTab === tab.id ? '1px solid var(--brand-edge)' : 'none',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: activeTab === tab.id ? 500 : 400,
                cursor: 'pointer',
                transition: 'all 120ms',
                whiteSpace: 'nowrap',
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* RIGHT: Form panel — glass card */}
        <div style={{
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--edge-1)',
          borderRadius: 18,
          padding: 26,
        }}>

          {/* ACCOUNT */}
          {activeTab === 'account' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-1)', margin: '0 0 22px' }}>Account</h2>
              <div style={{ display: 'grid', gap: 16, maxWidth: 480 }}>
                <FormField label="Name" value={user?.name || '—'} disabled />
                <FormField label="Email" value={user?.email || '—'} disabled />
                <FormField label="Role" value={user?.is_admin ? 'ADMIN' : 'MEMBER'} disabled />
                <div style={{ color: 'var(--text-3)', fontSize: 12, marginTop: 6 }}>
                  Profile fields are read-only. Email and name changes require admin support — drop a note via Settings → Notifications.
                </div>
              </div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {activeTab === 'notifications' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-1)', margin: '0 0 22px' }}>Notifications</h2>
              <div style={{ display: 'grid', gap: 14 }}>
                <NotifToggleField
                  label="Signal fired"
                  description="Email me when a fresh signal lands after the 4:15 PM IST scan."
                  checked={notifPrefs.signal_fired}
                  onChange={(v) => updateNotifPref('signal_fired', v)}
                />
                <NotifToggleField
                  label="Stop hit"
                  description="Email me when a position I hold hits its stop."
                  checked={notifPrefs.stop_hit}
                  onChange={(v) => updateNotifPref('stop_hit', v)}
                />
                <NotifToggleField
                  label="Daily summary"
                  description="A short end-of-day recap with portfolio and signal stats."
                  checked={notifPrefs.daily_summary}
                  onChange={(v) => updateNotifPref('daily_summary', v)}
                />
              </div>
              <div style={{
                color: 'var(--text-3)',
                fontSize: 12,
                marginTop: 14,
                paddingTop: 12,
                borderTop: '1px solid var(--edge-1)',
              }}>
                Saved locally for now. Email delivery hooks ship in a future release.
              </div>
            </div>
          )}

          {/* RISK CAPS */}
          {activeTab === 'risk' && (
            <RiskCapsPanel />
          )}

          {/* SECURITY */}
          {activeTab === 'security' && (
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-1)', margin: '0 0 22px' }}>Security</h2>
              <MfaPanel />
            </div>
          )}

        </div>
      </div>

      {/* Danger zone — sign out */}
      <div style={{ marginTop: 32 }}>
        <h2 className="t-title-2 flex items-baseline" style={{ margin: 0, color: 'var(--text-1)', fontSize: 18, fontWeight: 600 }}>
          <span
            aria-hidden="true"
            style={{
              display: 'inline-block',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--bear)',
              marginRight: 8,
              transform: 'translateY(-2px)',
              flexShrink: 0,
            }}
          />
          Danger zone
        </h2>
        <p style={{ color: 'var(--text-2)', margin: '4px 0 0', maxWidth: '76ch', fontSize: 12 }}>
          Sign out of Nifty Satvik on this device. Your sessions on other devices stay active.
        </p>
        <div style={{ marginTop: 12 }}>
          <button
            type="button"
            onClick={logout}
            className="t-ui-callout inline-flex items-center"
            style={{
              gap: 6,
              background: 'transparent',
              border: 'none',
              color: 'var(--bear)',
              padding: 0,
              cursor: 'pointer',
              fontWeight: 600,
              textDecoration: 'underline',
              textUnderlineOffset: 3,
              textDecorationColor: 'oklch(66% 0.21 25 / 0.4)',
              fontSize: 13,
            }}
          >
            <LogOut size={13} strokeWidth={1.75} />
            Sign out
          </button>
        </div>
      </div>
    </PageShell>
  );
}

// ══════════════════════════════════════════════════════════════
// MFA
// ══════════════════════════════════════════════════════════════

function MfaPanel() {
  const [status, setStatus] = useState({ enabled: null }); // null = loading
  const [setupData, setSetupData] = useState(null);        // { otpauth_uri, secret }
  const [verifyCode, setVerifyCode] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState('idle'); // 'idle' | 'enrolling' | 'disabling'

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchMfaStatus();
        if (!cancelled) setStatus({ enabled: !!data.enabled });
      } catch {
        if (!cancelled) setStatus({ enabled: false });
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const startEnrollment = async () => {
    setBusy(true);
    try {
      const data = await mfaSetup();
      setSetupData(data);
      setMode('enrolling');
    } catch (err) {
      toast.error(err.message || 'Failed to start enrollment.');
    } finally {
      setBusy(false);
    }
  };

  const submitVerify = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await mfaVerify(verifyCode);
      toast.success('Two-factor authentication enabled.');
      setStatus({ enabled: true });
      setSetupData(null);
      setVerifyCode('');
      setMode('idle');
    } catch (err) {
      toast.error(err.message || 'Invalid code.');
    } finally {
      setBusy(false);
    }
  };

  const submitDisable = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await mfaDisable(disablePassword);
      toast.success('Two-factor authentication disabled.');
      setStatus({ enabled: false });
      setDisablePassword('');
      setMode('idle');
    } catch (err) {
      toast.error(err.message || 'Failed to disable.');
    } finally {
      setBusy(false);
    }
  };

  if (status.enabled === null) {
    return (
      <div className="t-ui-footnote" style={{ padding: '14px 20px', color: 'var(--text-3)' }}>
        Loading…
      </div>
    );
  }

  return (
    <div style={{ padding: '14px 20px' }}>
      <div className="flex items-center justify-between" style={{ marginBottom: status.enabled || mode === 'idle' ? 12 : 0, gap: 12 }}>
        <span className="t-ui-callout" style={{ color: 'var(--text-3)' }}>Two-factor auth</span>
        {status.enabled
          ? <StatusChip tone="bull">ENABLED</StatusChip>
          : <StatusChip tone="muted">OFF</StatusChip>}
      </div>

      {/* IDLE STATE */}
      {mode === 'idle' && !status.enabled && (
        <button
          type="button"
          onClick={startEnrollment}
          disabled={busy}
          className="t-ui-callout"
          style={{
            padding: '9px 16px',
            background: 'transparent',
            color: 'var(--brand-hi)',
            border: '1px solid var(--brand-edge)',
            borderRadius: 'var(--r-chip)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          {busy ? 'Starting…' : 'Enable 2FA'}
        </button>
      )}
      {mode === 'idle' && status.enabled && (
        <button
          type="button"
          onClick={() => setMode('disabling')}
          className="t-ui-callout"
          style={{
            padding: '9px 16px',
            background: 'transparent',
            color: 'var(--text-2)',
            border: '1px solid var(--edge-2)',
            borderRadius: 'var(--r-chip)',
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          Disable 2FA
        </button>
      )}

      {/* ENROLLMENT STATE */}
      {mode === 'enrolling' && setupData && (
        <form
          onSubmit={submitVerify}
          style={{
            marginTop: 16, padding: 16,
            background: 'var(--surface-2)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            display: 'flex', flexDirection: 'column', gap: 14,
          }}
        >
          <div className="t-ui-body" style={{ color: 'var(--text-2)' }}>
            Scan this QR code with Google Authenticator, Authy, or 1Password, then enter the 6-digit code below to confirm.
          </div>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ background: '#fff', padding: 10, borderRadius: 8, lineHeight: 0 }}>
              <QRCodeSVG value={setupData.otpauth_uri} size={148} level="M" />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div className="t-ui-micro" style={{ color: 'var(--text-3)', marginBottom: 6 }}>
                Or enter manually
              </div>
              <code
                className="t-num-body"
                style={{
                  display: 'block', padding: '6px 10px',
                  background: 'var(--surface-3)', borderRadius: 'var(--r-chip)',
                  wordBreak: 'break-all',
                  border: '1px solid var(--edge-1)',
                }}
              >
                {setupData.secret}
              </code>
            </div>
          </div>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            pattern="[0-9]{6}"
            required
            placeholder="123456"
            value={verifyCode}
            onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            style={{
              padding: '10px 14px', fontSize: 16,
              background: 'var(--surface-3)',
              border: '1px solid var(--edge-1)',
              color: 'var(--text-1)',
              borderRadius: 'var(--r-chip)',
              letterSpacing: '0.4em', textAlign: 'center',
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
            }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              type="submit"
              disabled={busy || verifyCode.length !== 6}
              className="t-ui-callout"
              style={{
                padding: '9px 16px',
                background: 'var(--brand)', color: 'var(--brand-fg)',
                border: 'none', borderRadius: 'var(--r-chip)',
                fontWeight: 600,
                cursor: busy ? 'not-allowed' : 'pointer',
                opacity: busy || verifyCode.length !== 6 ? 0.6 : 1,
                display: 'inline-flex', alignItems: 'center', gap: 6,
              }}
            >
              {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Confirm and enable
            </button>
            <button
              type="button"
              onClick={() => { setMode('idle'); setSetupData(null); setVerifyCode(''); }}
              disabled={busy}
              className="t-ui-callout"
              style={{
                padding: '9px 16px',
                background: 'transparent', color: 'var(--text-2)',
                border: '1px solid var(--edge-1)', borderRadius: 'var(--r-chip)',
                fontWeight: 500, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* DISABLE STATE */}
      {mode === 'disabling' && (
        <form
          onSubmit={submitDisable}
          style={{
            marginTop: 16, padding: 16,
            background: 'var(--surface-2)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            display: 'flex', flexDirection: 'column', gap: 12,
          }}
        >
          <div className="t-ui-body" style={{ color: 'var(--text-2)' }}>
            Enter your password to confirm disabling 2FA.
          </div>
          <input
            type="password"
            autoComplete="current-password"
            required
            placeholder="Password"
            value={disablePassword}
            onChange={(e) => setDisablePassword(e.target.value)}
            className="t-ui-body"
            style={{
              padding: '10px 14px',
              background: 'var(--surface-3)',
              border: '1px solid var(--edge-1)',
              color: 'var(--text-1)',
              borderRadius: 'var(--r-chip)',
            }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            {/* Bordered, not solid — danger affordance lives in tone+text,
                not in a high-visual-weight bear button. */}
            <button
              type="submit"
              disabled={busy || !disablePassword}
              className="t-ui-callout"
              style={{
                padding: '9px 16px',
                background: 'transparent', color: 'var(--bear)',
                border: '1px solid var(--bear)', borderRadius: 'var(--r-chip)',
                fontWeight: 600,
                cursor: busy ? 'not-allowed' : 'pointer',
                opacity: busy || !disablePassword ? 0.6 : 1,
              }}
            >
              Disable 2FA
            </button>
            <button
              type="button"
              onClick={() => { setMode('idle'); setDisablePassword(''); }}
              disabled={busy}
              className="t-ui-callout"
              style={{
                padding: '9px 16px',
                background: 'transparent', color: 'var(--text-2)',
                border: '1px solid var(--edge-1)', borderRadius: 'var(--r-chip)',
                fontWeight: 500, cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// FORM HELPERS
// ══════════════════════════════════════════════════════════════

function FormField({ label, value, defaultValue, disabled, onChange }) {
  // Two modes: controlled (parent passes value + onChange) vs uncontrolled
  // (use defaultValue + internal state). Read-only profile fields use
  // controlled mode with no onChange; Risk caps uses controlled mode with
  // a parent-managed setter.
  const isControlled = onChange !== undefined;
  const [internalVal, setInternalVal] = React.useState(value ?? defaultValue ?? '');
  const val = isControlled ? (value ?? '') : internalVal;
  const handleChange = (e) => {
    if (isControlled) onChange(e);
    else setInternalVal(e.target.value);
  };
  return (
    <div>
      <label style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        color: 'var(--text-3)',
        display: 'block',
        marginBottom: 6,
        fontWeight: 600,
      }}>{label}</label>
      <input
        type="text"
        value={val}
        onChange={handleChange}
        disabled={disabled}
        style={{
          width: '100%',
          height: 36,
          padding: '0 12px',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid var(--edge-1)',
          borderRadius: 10,
          color: 'var(--text-1)',
          fontSize: 14,
          fontFamily: 'inherit',
          cursor: disabled ? 'not-allowed' : 'text',
          opacity: disabled ? 0.6 : 1,
        }}
      />
    </div>
  );
}

function NotifToggleField({ label, description, checked, onChange }) {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start',
      gap: 12,
      paddingBottom: 14,
      borderBottom: '1px solid var(--edge-1)',
    }}>
      <div>
        <div style={{ color: 'var(--text-1)', fontSize: 13, fontWeight: 500 }}>{label}</div>
        {description && (
          <p style={{ color: 'var(--text-3)', margin: '4px 0 0', maxWidth: '60ch', fontSize: 12 }}>
            {description}
          </p>
        )}
      </div>
      <Toggle checked={checked} onChange={onChange} />
    </div>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      style={{
        position: 'relative',
        width: 40,
        height: 22,
        borderRadius: 9999,
        background: checked ? 'var(--brand)' : 'var(--surface-3)',
        border: `1px solid ${checked ? 'var(--brand)' : 'var(--edge-1)'}`,
        cursor: 'pointer',
        transition: 'background var(--dur-press) ease, border-color var(--dur-press) ease',
        flexShrink: 0,
        padding: 0,
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 20 : 2,
          width: 16,
          height: 16,
          borderRadius: 9999,
          background: checked ? 'var(--brand-fg)' : 'var(--text-2)',
          transition: 'left var(--dur-hover) var(--ease-out-cubic)',
        }}
      />
    </button>
  );
}

const RISK_CAPS_STORAGE_KEY = 'nq_risk_caps';
const RISK_CAPS_DEFAULTS = { maxPositionPct: '8', maxSectorPct: '30', dailyLossPct: '3' };

function RiskCapsPanel() {
  const [draft, setDraft] = React.useState(RISK_CAPS_DEFAULTS);
  const [saved, setSaved] = React.useState(RISK_CAPS_DEFAULTS);

  React.useEffect(() => {
    try {
      const raw = localStorage.getItem(RISK_CAPS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        setDraft({ ...RISK_CAPS_DEFAULTS, ...parsed });
        setSaved({ ...RISK_CAPS_DEFAULTS, ...parsed });
      }
    } catch { /* corrupted localStorage — fall back to defaults */ }
  }, []);

  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);

  const handleSave = () => {
    try {
      localStorage.setItem(RISK_CAPS_STORAGE_KEY, JSON.stringify(draft));
      setSaved(draft);
      toast.success('Risk caps saved', {
        description: 'Stored on this device. Server-side enforcement ships with the next risk-engine release.',
      });
    } catch {
      toast.error('Could not save', { description: 'Local storage is unavailable in this browser.' });
    }
  };

  const handleCancel = () => setDraft(saved);

  const onField = (key) => (e) => setDraft((d) => ({ ...d, [key]: e.target.value }));

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-1)', margin: '0 0 22px' }}>Risk caps</h2>
      <div style={{ display: 'grid', gap: 16, maxWidth: 480 }}>
        <FormField label="Max position %" value={draft.maxPositionPct} onChange={onField('maxPositionPct')} />
        <FormField label="Max sector exposure %" value={draft.maxSectorPct} onChange={onField('maxSectorPct')} />
        <FormField label="Daily loss limit %" value={draft.dailyLossPct} onChange={onField('dailyLossPct')} />
        <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
          <button
            type="button"
            onClick={handleSave}
            disabled={!dirty}
            style={{
              background: 'var(--brand-grad)',
              color: 'white',
              border: 'none',
              padding: '10px 22px',
              borderRadius: 999,
              fontSize: 13,
              fontWeight: 600,
              boxShadow: '0 6px 18px rgba(79,140,255,0.4)',
              cursor: dirty ? 'pointer' : 'not-allowed',
              opacity: dirty ? 1 : 0.5,
            }}
          >
            Save
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={!dirty}
            style={{
              background: 'rgba(255,255,255,0.04)',
              color: 'var(--text-2)',
              border: '1px solid var(--edge-1)',
              padding: '10px 22px',
              borderRadius: 999,
              fontSize: 13,
              cursor: dirty ? 'pointer' : 'not-allowed',
              opacity: dirty ? 1 : 0.5,
            }}
          >
            Cancel
          </button>
        </div>
        <div style={{ color: 'var(--text-3)', fontSize: 12, paddingTop: 4 }}>
          Saved on this device for now. Server-side enforcement ships with the next risk-engine release.
        </div>
      </div>
    </div>
  );
}
