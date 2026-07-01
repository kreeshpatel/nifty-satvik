/**
 * FundsV2 — Phase 6 redesign of the Funds page.
 *
 * Reads /api/kite/margins (Kite is the source of truth per product decision —
 * external Kite trades, deposits, withdrawals all hit Kite directly).
 * Renders two segment cards (Equity / Commodity), each showing available,
 * used, and total breakdowns. Falls back to a Connect-Kite empty state
 * when the user hasn't linked their broker.
 *
 * Layout:
 *   Page title + Kite chip
 *   ────────────────────────────────────────
 *   Segment cards (2-up): EQUITY · COMMODITY
 *     Each shows:
 *       - Available cash
 *       - Used margin (with breakdown — span, exposure, holding sales, etc.)
 *       - Total balance
 *       - Collateral (if non-zero)
 */
import React, { useContext } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Plug, RefreshCcw, AlertCircle } from 'lucide-react';
import { PageShell } from '@/components/shared/PageShell';
import { EmptyCard } from '@/components/shared/EmptyCard';
import { kiteMargins } from '@/services/api';
import { KiteContext } from '@/App';
import { fmtINR } from '@/lib/format';

/**
 * Local raw-margins query — useKiteMargins in queries/useKiteState.js
 * normalizes to { available, used, total } for the equity segment only.
 * The Funds page wants the FULL response so it can show both equity AND
 * commodity segments.
 */
function useRawMargins({ enabled = true } = {}) {
  return useQuery({
    queryKey: ['kite', 'margins-raw'],
    queryFn: kiteMargins,
    enabled,
    staleTime: 30 * 1000,
    gcTime: 5 * 60 * 1000,
  });
}

// Equity-segment summary numbers used by the hero KPI strip. Pulled into
// a helper so the KPI math has one source of truth and SegmentCard's
// per-segment numbers stay independent.
function equityHeroNumbers(equity) {
  if (!equity) {
    return { available: 0, used: 0, pnl: 0, hasData: false };
  }
  const available = Number(
    equity?.available?.live_balance ??
      equity?.available?.cash ??
      equity?.available?.intraday_payin ??
      0,
  );
  const used = Number(equity?.utilised?.debits ?? 0);
  // Kite returns realised P&L (m2m_realised) and unrealised P&L (m2m_unrealised)
  // inside the utilised block. They're already signed (+/-) so we sum and let
  // the tone follow the result.
  const realised = Number(equity?.utilised?.m2m_realised ?? 0);
  const unrealised = Number(equity?.utilised?.m2m_unrealised ?? 0);
  const pnl = realised + unrealised;
  return { available, used, pnl, hasData: true };
}

export default function FundsV2() {
  const kite = useContext(KiteContext);
  const marginsQuery = useRawMargins({ enabled: !!kite?.connected });
  const data = marginsQuery.data ?? {};
  const equity = data?.equity ?? null;
  const commodity = data?.commodity ?? null;
  const hero = equityHeroNumbers(equity);

  return (
    <PageShell title="Funds" heroTone="bull">
      <header style={{ paddingBottom: 32 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            gap: 16,
            marginBottom: 0,
          }}
        >
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 28,
              fontWeight: 600,
              margin: 0,
              color: 'var(--text-1)',
              letterSpacing: '-0.018em',
            }}
          >
            Funds
          </h1>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 13,
              color: 'var(--text-3)',
              fontWeight: 400,
            }}
          >
            Synced from Zerodha Kite
          </span>
        </div>
      </header>

      {!kite?.connected ? (
        <EmptyCard
          variant="warn"
          icon={<Plug size={16} strokeWidth={1.75} />}
          title="Connect Kite to see your funds"
          body="Funds are read live from your Zerodha account. We never touch deposits or withdrawals — those happen in Kite directly."
          action={
            <button
              type="button"
              onClick={kite?.connect}
              className="t-ui-callout"
              style={{
                padding: '10px 18px',
                background: 'var(--brand)',
                color: 'var(--brand-fg)',
                border: '1px solid var(--brand)',
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Connect Kite →
            </button>
          }
        />
      ) : marginsQuery.isLoading ? (
        <SegmentSkeleton />
      ) : marginsQuery.error ? (
        <EmptyCard
          variant="warn"
          icon={<AlertCircle size={16} strokeWidth={1.75} />}
          title="Couldn't load funds"
          body={marginsQuery.error?.message || 'Try refreshing.'}
          action={
            <button
              type="button"
              onClick={() => marginsQuery.refetch()}
              className="t-ui-callout"
              style={{
                padding: '10px 18px',
                background: 'transparent',
                color: 'var(--text-2)',
                border: '1px solid var(--edge-2)',
                borderRadius: 'var(--r-chip)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <RefreshCcw size={14} strokeWidth={1.75} />
              Retry
            </button>
          }
        />
      ) : (
        <>
          {/* KPI STRIP — 3 glass cards (AVAILABLE CASH, MARGIN USED, UNREALISED P&L) */}
          <section
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: 14,
              marginBottom: 22,
            }}
          >
            {/* Card 1: Available Cash */}
            <div
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-card)',
                backdropFilter: 'blur(24px) saturate(140%)',
                boxShadow: 'var(--shadow-glass)',
                padding: 22,
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9.5,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: 'var(--text-3)',
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Available cash
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 32,
                  color: 'var(--text-1)',
                  lineHeight: 1,
                  marginBottom: 10,
                }}
              >
                {fmtINR(hero.available)}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-3)',
                }}
              >
                {hero.available > 0
                  ? `${Math.round((hero.available / (hero.available + hero.used)) * 100)}% of total`
                  : '—'}
              </div>
            </div>

            {/* Card 2: Margin Used */}
            <div
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-card)',
                backdropFilter: 'blur(24px) saturate(140%)',
                boxShadow: 'var(--shadow-glass)',
                padding: 22,
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9.5,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: 'var(--text-3)',
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Margin used
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 32,
                  color: 'var(--text-1)',
                  lineHeight: 1,
                  marginBottom: 10,
                }}
              >
                {fmtINR(hero.used)}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-3)',
                }}
              >
                {hero.used > 0
                  ? `${Math.round((hero.used / (hero.available + hero.used)) * 100)}% · Open positions`
                  : '—'}
              </div>
            </div>

            {/* Card 3: Unrealised P&L */}
            <div
              style={{
                background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-card)',
                backdropFilter: 'blur(24px) saturate(140%)',
                boxShadow: 'var(--shadow-glass)',
                padding: 22,
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 9.5,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: 'var(--text-3)',
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Unrealised P&amp;L
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontVariantNumeric: 'tabular-nums',
                  fontSize: 32,
                  color: hero.pnl >= 0 ? 'var(--bull)' : 'var(--bear)',
                  lineHeight: 1,
                  marginBottom: 10,
                }}
              >
                {hero.pnl === 0 ? '₹0' : `${hero.pnl >= 0 ? '+' : ''}${fmtINR(hero.pnl)}`}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--text-3)',
                }}
              >
                {hero.pnl >= 0 ? '+' : ''}
                {((hero.pnl / (hero.available + hero.used)) * 100).toFixed(2)}% today
              </div>
            </div>
          </section>

          {/* TODAY'S FUND MOVEMENTS TABLE */}
          <div
            style={{
              background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%)',
              border: '1px solid var(--edge-1)',
              borderRadius: 'var(--r-card)',
              backdropFilter: 'blur(24px) saturate(140%)',
              boxShadow: 'var(--shadow-glass)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                padding: '22px',
                borderBottom: '1px solid var(--edge-1)',
              }}
            >
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 600,
                  color: 'var(--text-1)',
                }}
              >
                Today's fund movements
              </div>
            </div>

            {/* HONESTY: this previously rendered a hardcoded mock fund-movements
                table (fabricated INFY/ASIANPAINT/RELIANCE rows) as if real, to
                Kite-connected users. No live fund-movement ledger is wired up,
                so show an explicit empty state instead of fabricated data. */}
            <div style={{ padding: '16px 22px' }}>
              <EmptyCard
                variant="muted"
                title="Fund movements aren't wired up yet"
                body="A live fund-movement ledger isn't connected here yet. See the Orders tab for today's order activity."
              />
            </div>
          </div>
        </>
      )}
    </PageShell>
  );
}


function SegmentSkeleton() {
  return (
    <section
      className="grid"
      style={{
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))',
        gap: 16,
      }}
    >
      {[0, 1].map((i) => (
        <div
          key={i}
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-card)',
            padding: 'var(--pad-card-lg)',
            minHeight: 280,
            animation: 'skelPulse 1.8s ease-in-out infinite',
          }}
        >
          <div style={{ height: 18, width: 100, background: 'var(--surface-2)', borderRadius: 4 }} />
          <div style={{ height: 36, width: 200, background: 'var(--surface-2)', borderRadius: 4, marginTop: 24 }} />
          <div style={{ height: 12, width: 120, background: 'var(--surface-2)', borderRadius: 4, marginTop: 8 }} />
          <div style={{ marginTop: 24, borderTop: '1px solid var(--edge-1)', paddingTop: 12 }}>
            {Array.from({ length: 3 }).map((_, j) => (
              <div
                key={j}
                style={{
                  height: 14,
                  background: 'var(--surface-2)',
                  borderRadius: 4,
                  marginBottom: 12,
                }}
              />
            ))}
          </div>
        </div>
      ))}
      <style>{`@keyframes skelPulse { 0%, 100% { opacity: 1 } 50% { opacity: 0.6 } }`}</style>
    </section>
  );
}
