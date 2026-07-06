import React, { useContext } from 'react';
import { Loader2 } from 'lucide-react';
import { KiteContext } from '@/App';
import kiteMark from '@/assets/brand/kite-logo.png';

/**
 * KiteChip — top-bar Kite (Zerodha) integration status pill.
 *
 * Connected  → orange Kite mark + "Kite" + green live dot (click disconnects).
 * Disconnected → amber-tinted "Connect" (click launches the Kite OAuth flow).
 * Connecting → spinner.
 *
 * All state comes from KiteContext (App.js), the single source of truth for
 * the shared owner Kite session. Rendered on the desktop top bar only; mobile
 * keeps the connect/disconnect action inside the account drawer.
 */
export default function KiteChip() {
  const kite = useContext(KiteContext);
  const connected = !!kite?.connected;
  const connecting = !!kite?.connecting;

  const onClick = () => {
    if (connecting) return;
    if (connected) kite?.disconnect?.();
    else kite?.connect?.();
  };

  const title = connected
    ? `Kite connected${kite?.userId ? ` · ${kite.userId}` : ''} — click to disconnect`
    : 'Connect your Kite (Zerodha) account for live orders';

  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        height: 34,
        padding: '0 12px',
        background: connected ? 'rgba(255,255,255,0.05)' : 'rgba(255,138,0,0.10)',
        border: `1px solid ${connected ? 'var(--edge-1)' : 'rgba(255,138,0,0.35)'}`,
        borderRadius: 999,
        cursor: 'pointer',
        color: 'var(--text-1)',
        fontFamily: 'var(--font-sans)',
        fontSize: 12.5,
        fontWeight: 600,
        whiteSpace: 'nowrap',
        transition: 'all 200ms',
      }}
    >
      {connecting ? (
        <Loader2 size={15} className="animate-spin" />
      ) : (
        <img
          src={kiteMark}
          alt=""
          width={16}
          height={16}
          style={{ width: 16, height: 16, objectFit: 'contain', display: 'block', flexShrink: 0 }}
        />
      )}
      <span>{connecting ? 'Connecting' : connected ? 'Kite' : 'Connect'}</span>
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: '50%',
          background: connected ? 'var(--bull)' : 'var(--text-3)',
          boxShadow: connected ? '0 0 6px var(--bull)' : 'none',
        }}
      />
    </button>
  );
}
