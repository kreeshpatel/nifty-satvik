/**
 * Company page — product definition §13 (docs/DESIGN_BRIEF_V5.md): the Yahoo-style basics for any
 * NSE stock, plus OUR CALL on it when we have issued one. Shared data (docs/DATA_MAP.md §1).
 * Every panel fetches independently (one failing provider call degrades one panel, not the page):
 *   quote        GET /api/yahoo/quote/{sym}         last_price, change, change_pct, open/high/low,
 *                                                    previous_close, volume, 52w, market_cap, pe, as_of
 *   chart        GET /api/yahoo/historical/{sym}    [[date, o, h, l, c, v], …]
 *   statistics   GET /api/yahoo/fundamentals/{sym}  valuation, profitability, trading, ownership
 *   shareholding GET /api/yahoo/shareholding/{sym}  promoters / fii / public (%)
 *   peers        GET /api/yahoo/peers/{sym}         [{symbol, name, ltp, change_pct, pe, pb, mcap, is_target}]
 *   news         GET /api/yahoo/news/{sym}          [{title, publisher, link, published}]
 *   our call     /api/signals (current book) + /api/signals/history, matched by ticker
 * Refresh: quote every 5 min while NSE is open (else on focus); fundamentals/peers/shareholding daily.
 */
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import LwChart from '@/components/charts/LwChart';
import { yahooQuote, yahooHistorical, yahooFundamentals, yahooShareholding, yahooPeers, yahooNews } from '@/services/api';
import { useSignals } from '@/hooks/queries/useSignals';
import useSignalHistory from '@/hooks/queries/useSignalHistory';
import { isMarketOpen } from '@/lib/schedule';
import { DISCLAIMER } from '@/lib/signalCopy';
import '@/styles/dashboard-v5.css';

const MINUS = '−';
const n = (v) => (v == null || v === '' || Number.isNaN(Number(v)) ? null : Number(v));
const fmt = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; const s = Math.abs(x).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp }); return `${x < 0 ? MINUS : ''}${s}`; };
const pct = (v, dp = 2) => { const x = n(v); if (x == null) return '—'; if (Math.abs(x) < 0.5 * 10 ** -dp) return `${(0).toFixed(dp)}%`; return `${x > 0 ? '▲ +' : `▼ ${MINUS}`}${Math.abs(x).toFixed(dp)}%`; };
const tone = (v) => (n(v) == null || Math.abs(n(v)) < 0.005 ? '' : n(v) > 0 ? 'up' : 'down');
/** ₹ amounts in Indian units: lakh crore / crore / lakh. */
const inrBig = (v) => {
  const x = n(v); if (x == null) return '—';
  const a = Math.abs(x);
  const s = a >= 1e12 ? `${fmt(a / 1e12, 2)}L Cr` : a >= 1e7 ? `${fmt(a / 1e7, 0)} Cr` : a >= 1e5 ? `${fmt(a / 1e5, 1)} L` : fmt(a, 0);
  return `${x < 0 ? MINUS : ''}₹${s}`;
};
const ratio = (v, dp = 2) => (n(v) == null ? '—' : fmt(v, dp));
const frac = (v) => (n(v) == null ? '—' : `${fmt(n(v) * 100, 2)}%`);      // provider gives 0.123 = 12.3%
const vol = (v) => { const x = n(v); if (x == null) return '—'; return x >= 1e7 ? `${fmt(x / 1e7, 2)} Cr` : x >= 1e5 ? `${fmt(x / 1e5, 2)} L` : fmt(x, 0); };
const dmy = (d) => (d ? new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : '—');

const PERIODS = [['1M', '1d', '1mo'], ['6M', '1d', '6mo'], ['1Y', '1d', '1y'], ['5Y', '1wk', '5y'], ['Max', '1mo', 'max']];

function Panel({ id, title, meta, action, children, className = '' }) {
  return (
    <section className={`d7-panel ${className}`} aria-labelledby={`${id}-h`}>
      <header className="d7-panel-head"><h2 id={`${id}-h`}>{title}</h2>{meta && <span className="d7-panel-meta">{meta}</span>}{action && <span className="d7-panel-act">{action}</span>}</header>
      {children}
    </section>
  );
}
const Failed = ({ what }) => <p className="d7-empty">{what} is unavailable from the data provider right now. Use Refresh in the strip above to retry.</p>;
const Skel = ({ rows = 3 }) => <div aria-busy="true">{Array.from({ length: rows }).map((_, i) => <div key={i} className="d7-skel" />)}</div>;

function KV({ rows }) {
  return <dl className="d7-kv">{rows.map(([k, v, t]) => <div key={k}><dt>{k}</dt><dd data-num className={t || ''}>{v}</dd></div>)}</dl>;
}

function Range52({ low, high, last }) {
  const lo = n(low), hi = n(high), p = n(last);
  if (lo == null || hi == null || hi <= lo) return <span className="d7-muted">—</span>;
  const pos = p == null ? null : Math.max(0, Math.min(100, ((p - lo) / (hi - lo)) * 100));
  return (
    <span className="s7-range" role="img" aria-label={`52-week range ${fmt(lo)} to ${fmt(hi)}${p != null ? `, last ${fmt(p)}` : ''}`}>
      <span className="s7-range-l" data-num>{fmt(lo)}</span>
      <span className="s7-range-bar">{pos != null && <span style={{ left: `${pos}%` }} />}</span>
      <span className="s7-range-h" data-num>{fmt(hi)}</span>
    </span>
  );
}

export default function StockV7() {
  const { symbol: raw } = useParams();
  const sym = decodeURIComponent(raw || '').toUpperCase();
  const [per, setPer] = useState('1Y');
  const [kind, setKind] = useState('candles');
  const [, interval, period] = PERIODS.find((p) => p[0] === per);
  const day = 24 * 60 * 60 * 1000;

  const quote = useQuery({ queryKey: ['yahoo', 'quote', sym], queryFn: () => yahooQuote(sym), enabled: !!sym, staleTime: 60 * 1000,
    refetchInterval: () => (isMarketOpen() ? 5 * 60 * 1000 : false), retry: 1 });
  const hist = useQuery({ queryKey: ['yahoo', 'hist', sym, interval, period], queryFn: () => yahooHistorical(sym, interval, period), enabled: !!sym, staleTime: 10 * 60 * 1000, retry: 1 });
  const fund = useQuery({ queryKey: ['yahoo', 'fund', sym], queryFn: () => yahooFundamentals(sym), enabled: !!sym, staleTime: day, retry: 1 });
  const share = useQuery({ queryKey: ['yahoo', 'share', sym], queryFn: () => yahooShareholding(sym), enabled: !!sym, staleTime: day, retry: 1 });
  const peers = useQuery({ queryKey: ['yahoo', 'peers', sym], queryFn: () => yahooPeers(sym), enabled: !!sym, staleTime: day, retry: 1 });
  const news = useQuery({ queryKey: ['yahoo', 'news', sym], queryFn: () => yahooNews(sym), enabled: !!sym, staleTime: 30 * 60 * 1000, retry: 1 });
  const sq = useSignals({ model: 'bhanushali' });
  const hq = useSignalHistory({});

  const q = quote.data || {};
  const f = fund.data || {};
  const last = n(q.last_price);
  // Dividend yield: computed (annual dividend per share / price) — the provider's dividendYield
  // field has changed units across versions, so it is used only as a fallback, read as a percent.
  const divYield = n(f.dividend_rate) != null && last ? `${fmt((n(f.dividend_rate) / last) * 100, 2)}%`
    : n(f.dividend_yield) != null ? `${fmt(f.dividend_yield, 2)}%` : '—';

  // our calls on this stock: the current book first, then the issued history (newest first)
  const calls = useMemo(() => {
    const cur = (sq.data?.signals ?? []).filter((s) => String(s.ticker).toUpperCase() === sym);
    const past = (hq.data?.history ?? []).filter((s) => String(s.ticker).toUpperCase() === sym);
    const seen = new Set(cur.map((s) => s.signal_date));
    return [...cur, ...past.filter((s) => !seen.has(s.signal_date))].sort((a, b) => String(b.signal_date).localeCompare(String(a.signal_date)));
  }, [sq.data, hq.data, sym]);
  const call = calls[0];

  const candles = useMemo(() => {
    const rows = Array.isArray(hist.data) ? hist.data : [];
    const m = new Map();
    rows.forEach((r) => { if (Array.isArray(r) && r.length >= 5) m.set(String(r[0]).slice(0, 10), r); });
    return [...m.entries()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([time, r]) => ({ time, open: +r[1], high: +r[2], low: +r[3], close: +r[4], volume: +r[5] || 0 }));
  }, [hist.data]);
  const chartSeries = useMemo(() => {
    if (!candles.length) return [];
    const main = kind === 'candles'
      ? { type: 'candles', data: candles.map(({ time, open, high, low, close }) => ({ time, open, high, low, close })), title: sym }
      : { type: 'area', data: candles.map((c) => ({ time: c.time, value: c.close })), color: '#20C4A0', title: sym };
    const volume = { type: 'volume', data: candles.map((c) => ({ time: c.time, value: c.volume, color: c.close >= c.open ? 'rgba(32,196,160,.35)' : 'rgba(255,107,74,.35)' })) };
    return [main, volume];
  }, [candles, kind, sym]);
  const perChange = candles.length > 1 ? ((candles[candles.length - 1].close / candles[0].close) - 1) * 100 : null;

  const peerRows = Array.isArray(peers.data) ? peers.data : (peers.data?.peers ?? []);
  const newsRows = Array.isArray(news.data) ? news.data : (news.data?.news ?? []);
  const sh = share.data || {};
  const shRows = [['Promoters', n(sh.promoters)], ['FII', n(sh.fii)], ['Public & others', n(sh.public)]].filter(([, v]) => v != null);

  return (
    <div className="d7">
      <header className="s7-head">
        <div className="s7-id">
          <p className="d7-sub"><Link to="/premove" className="d7-link">Research</Link> / {f.exchange || 'NSE'}</p>
          <h1>{sym}<span className="s7-name">{f.name || q.name || ''}</span></h1>
          <p className="d7-sub">{[f.sector, f.industry].filter(Boolean).join(' · ') || (fund.isLoading ? 'Loading…' : '')}</p>
        </div>
        <div className="s7-px">
          {quote.isLoading ? <div className="d7-skel" style={{ width: 220 }} /> : quote.error ? <p className="d7-muted">Price unavailable</p> : (
            <>
              <p className="s7-last" data-num>₹{fmt(last)}</p>
              <p className={`s7-chg ${tone(q.change)}`} data-num>{q.change != null ? `${n(q.change) > 0 ? '+' : n(q.change) < 0 ? MINUS : ''}${fmt(Math.abs(n(q.change)))}` : '—'} ({pct(q.change_pct)})</p>
              <p className="d7-sub2">{q.as_of ? `As of ${new Date(q.as_of).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })} IST` : 'Last session'} · delayed</p>
            </>
          )}
        </div>
      </header>

      <dl className="d7-stats s7-strip" aria-label="Today">
        <div><dt>Open</dt><dd data-num>{fmt(q.open)}</dd></div>
        <div><dt>Day range</dt><dd data-num>{fmt(q.low)} – {fmt(q.high)}</dd></div>
        <div><dt>Prev close</dt><dd data-num>{fmt(q.previous_close)}</dd></div>
        <div><dt>Volume</dt><dd data-num>{vol(q.volume)}</dd><span className="d7-sub2">avg {vol(f.avg_volume)}</span></div>
        <div><dt>52-week range</dt><dd><Range52 low={q.fifty_two_week_low ?? f.fifty_two_week_low} high={q.fifty_two_week_high ?? f.fifty_two_week_high} last={last} /></dd></div>
        <div><dt>Market cap</dt><dd data-num>{inrBig(q.market_cap ?? f.market_cap)}</dd><span className="d7-sub2">P/E {ratio(q.pe_ratio ?? f.pe_ratio)}</span></div>
      </dl>

      <div className="d7-grid">
        <div className="d7-main">
          <Panel id="chart" title="Price" meta={perChange != null ? <span className={tone(perChange)}>{pct(perChange)} over {per}</span> : null}
            action={(
              <span className="d7-tools">
                <span className="seg" role="tablist" aria-label="Period">
                  {PERIODS.map(([k]) => <button key={k} type="button" role="tab" aria-selected={per === k} className={per === k ? 'on' : ''} onClick={() => setPer(k)}>{k}</button>)}
                </span>
                <span className="seg" role="tablist" aria-label="Chart type">
                  {[['candles', 'Candles'], ['line', 'Line']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={kind === k} className={kind === k ? 'on' : ''} onClick={() => setKind(k)}>{l}</button>)}
                </span>
              </span>
            )}>
            {hist.isLoading ? <Skel rows={6} /> : hist.error || !candles.length ? <Failed what="Price history" /> : (
              <div className="d7-chart"><LwChart series={chartSeries} height={340} label={`${sym} price, ${per}`} /></div>
            )}
          </Panel>

          <div className="d7-two s7-three">
            <Panel id="val" title="Valuation">
              {fund.isLoading ? <Skel /> : fund.error ? <Failed what="Valuation" /> : (
                <KV rows={[['Market cap', inrBig(f.market_cap)], ['Enterprise value', inrBig(f.enterprise_value)], ['P/E (trailing)', ratio(f.pe_ratio)],
                  ['P/E (forward)', ratio(f.forward_pe)], ['P/B', ratio(f.price_to_book ?? f.pb_ratio)], ['PEG', ratio(f.peg_ratio)], ['EPS', fmt(f.eps)], ['Book value / share', fmt(f.book_value)]]} />
              )}
            </Panel>
            <Panel id="prof" title="Profitability & balance sheet">
              {fund.isLoading ? <Skel /> : fund.error ? <Failed what="Fundamentals" /> : (
                <KV rows={[['Revenue (TTM)', inrBig(f.revenue)], ['Profit margin', frac(f.profit_margin), tone(f.profit_margin)], ['Operating margin', frac(f.operating_margin), tone(f.operating_margin)],
                  ['ROE', frac(f.roe), tone(f.roe)], ['ROA', frac(f.roa), tone(f.roa)], ['Debt / equity', ratio(f.debt_to_equity)],
                  ['Dividend yield', divYield], ['Beta', ratio(f.beta)]]} />
              )}
            </Panel>
            <Panel id="trade" title="Trading & ownership">
              {fund.isLoading ? <Skel /> : fund.error ? <Failed what="Trading data" /> : (
                <KV rows={[['50-day average', fmt(f.fifty_day_avg)], ['200-day average', fmt(f.two_hundred_day_avg)], ['Avg volume (3M)', vol(f.avg_volume)], ['Avg volume (10D)', vol(f.avg_volume_10d)],
                  ['Shares outstanding', vol(f.shares_outstanding)], ['Free float', vol(f.float_shares)], ['Held by insiders', frac(f.held_percent_insiders)], ['Held by institutions', frac(f.held_percent_institutions)]]} />
              )}
            </Panel>
          </div>

          <Panel id="peers" title="Peers" meta="same industry">
            {peers.isLoading ? <Skel /> : peers.error ? <Failed what="Peer comparison" /> : peerRows.length === 0 ? <p className="d7-empty">No peers listed.</p> : (
              <div className="d7-tw"><table className="d7-t">
                <thead><tr><th scope="col">Company</th><th scope="col" className="r">Last</th><th scope="col" className="r">Change</th><th scope="col" className="r">Market cap</th><th scope="col" className="r">P/E</th><th scope="col" className="r">P/B</th><th scope="col" className="r">Div. yield</th></tr></thead>
                <tbody>{peerRows.map((p) => (
                  <tr key={p.symbol} className={`d7-static${p.is_target ? ' s7-self' : ''}`}>
                    <th scope="row"><Link to={`/stock/${encodeURIComponent(p.symbol)}`}>{p.symbol}</Link><span className="d7-qty">{p.name}</span></th>
                    <td className="r" data-num>{fmt(p.ltp)}</td><td className={`r ${tone(p.change_pct)}`} data-num>{pct(p.change_pct)}</td>
                    <td className="r" data-num>{inrBig(p.market_cap)}</td><td className="r" data-num>{ratio(p.pe_ratio)}</td><td className="r" data-num>{ratio(p.pb_ratio)}</td>
                    <td className="r" data-num>{p.dividend_yield != null ? `${fmt(p.dividend_yield, 2)}%` : '—'}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Panel>
        </div>

        <aside className="d7-side" aria-label="Our call, shareholding and news">
          <Panel id="call" title="Our call" meta={calls.length > 1 ? `${calls.length} issued on ${sym}` : null}>
            {(sq.isLoading || hq.isLoading) ? <Skel rows={2} /> : !call ? (
              <p className="d7-empty">We have not issued a call on {sym}. Research lists every call we have issued.</p>
            ) : (
              <>
                <KV rows={[
                  ['Issued', dmy(call.signal_date)],
                  ['Status', call.status === 'ACTIVE' || call.status === 'FRESH' ? (call.status === 'FRESH' ? 'New — buy window open' : 'Open') : 'Closed', call.status === 'FRESH' ? 'acc' : ''],
                  ['Entry', fmt(call.entry)],
                  ['Stop', fmt(call.stop), 'down'],
                  ['Target', fmt(call.target), 'up'],
                  ['Return since issue', pct(call.return_pct ?? (n(call.entry) && last != null ? ((last - call.entry) / call.entry) * 100 : null), 1), tone(call.return_pct ?? (n(call.entry) && last != null ? last - call.entry : null))],
                ]} />
                {call.sell_guidance?.headline && <p className="d7-note"><b>{call.sell_guidance.headline}</b></p>}
                <p className="d7-note"><Link to="/premove" className="d7-link">See it in Research →</Link></p>
              </>
            )}
          </Panel>

          <Panel id="share" title="Shareholding" meta="latest filing">
            {share.isLoading ? <Skel rows={2} /> : share.error || shRows.length === 0 ? <Failed what="Shareholding" /> : (
              <table className="d7-t d7-t-compact"><tbody>{shRows.map(([k, v]) => (
                <tr key={k} className="d7-static"><th scope="row" style={{ fontFamily: 'var(--sans)', fontWeight: 500 }}>{k}<span className="d7-bar" aria-hidden><span style={{ width: `${Math.min(100, v)}%` }} /></span></th><td className="r" data-num>{fmt(v, 1)}%</td></tr>
              ))}</tbody></table>
            )}
          </Panel>

          <Panel id="news" title="News">
            {news.isLoading ? <Skel rows={3} /> : news.error ? <Failed what="News" /> : newsRows.length === 0 ? <p className="d7-empty">No recent news.</p> : (
              <ul className="s7-news">{newsRows.slice(0, 8).map((a, i) => (
                <li key={a.link || i}>
                  <a href={a.link} target="_blank" rel="noopener noreferrer">{a.title}<ExternalLink size={12} aria-hidden /></a>
                  <span className="d7-sub2">{[a.publisher, a.published ? dmy(typeof a.published === 'number' ? a.published * 1000 : a.published) : null].filter(Boolean).join(' · ')}</span>
                </li>
              ))}</ul>
            )}
          </Panel>
        </aside>
      </div>

      <footer className="d7-disc">Market data from Yahoo Finance via our server, delayed; fundamentals as reported by the provider. {DISCLAIMER} Not SEBI-registered. Charts by TradingView Lightweight Charts™.</footer>
    </div>
  );
}
