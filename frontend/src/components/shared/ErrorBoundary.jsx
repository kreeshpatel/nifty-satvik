import React from 'react';
import { AlertOctagon, RefreshCcw } from 'lucide-react';

/**
 * ErrorBoundary — catches runtime errors thrown during render of child trees.
 *
 * Without this, an uncaught error in a page component (e.g. StockDetailV2)
 * causes React to unmount the entire route tree, leaving the user staring
 * at a black background with no information. With this, we render a useful
 * card showing the error message + a Reload button.
 *
 * Rendered just inside the Suspense fallback in App.js so it scopes to the
 * current route — the rest of the app shell (sidebar, header) keeps working.
 */
export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Log to console in production so the user can copy/paste it for support.
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
    this.setState({ info });
  }

  reset = () => this.setState({ error: null, info: null });

  render() {
    if (!this.state.error) return this.props.children;

    const message = this.state.error?.message || String(this.state.error || 'Unknown error');
    const stack = this.state.error?.stack || '';

    return (
      <div
        role="alert"
        style={{
          padding: 32,
          maxWidth: 720,
          margin: '40px auto',
          background: 'var(--surface-1)',
          border: '1px solid var(--bear)',
          borderRadius: 'var(--r-card)',
          boxShadow: 'var(--shadow-sm)',
          color: 'var(--text-1)',
          fontFamily: 'var(--font-sans)',
        }}
      >
        <div className="flex items-start" style={{ gap: 14, marginBottom: 16 }}>
          <div
            style={{
              width: 36, height: 36, flexShrink: 0,
              borderRadius: 'var(--r-chip)',
              background: 'var(--bear-soft)',
              border: '1px solid var(--bear)',
              color: 'var(--bear)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AlertOctagon size={18} strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <h2 className="t-title-2" style={{ margin: 0, color: 'var(--text-1)' }}>
              Something broke on this page
            </h2>
            <p className="t-ui-body" style={{ color: 'var(--text-2)', margin: '6px 0 0' }}>
              The component crashed mid-render. Reloading usually clears it. If it keeps
              happening, the message + stack below tells us exactly where to look.
            </p>
          </div>
        </div>

        <pre
          style={{
            padding: 14,
            background: 'var(--surface-2)',
            border: '1px solid var(--edge-1)',
            borderRadius: 'var(--r-chip)',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: 'var(--bear)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            overflowX: 'auto',
            maxHeight: 200,
            margin: 0,
          }}
        >
          {message}
        </pre>

        {stack && (
          <details style={{ marginTop: 12 }}>
            <summary
              className="t-ui-callout"
              style={{ color: 'var(--text-3)', cursor: 'pointer', userSelect: 'none' }}
            >
              Stack trace
            </summary>
            <pre
              style={{
                padding: 14,
                marginTop: 8,
                background: 'var(--surface-2)',
                border: '1px solid var(--edge-1)',
                borderRadius: 'var(--r-chip)',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--text-3)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                overflowX: 'auto',
                maxHeight: 320,
              }}
            >
              {stack}
            </pre>
          </details>
        )}

        <div className="flex" style={{ gap: 8, marginTop: 16 }}>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="t-ui-callout"
            style={{
              padding: '10px 18px',
              background: 'var(--brand)',
              color: 'var(--brand-fg)',
              border: '1px solid var(--brand)',
              borderRadius: 'var(--r-chip)',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <RefreshCcw size={14} strokeWidth={1.75} /> Reload page
          </button>
          <button
            type="button"
            onClick={this.reset}
            className="t-ui-callout"
            style={{
              padding: '10px 18px',
              background: 'transparent',
              color: 'var(--text-2)',
              border: '1px solid var(--edge-2)',
              borderRadius: 'var(--r-chip)',
              cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
