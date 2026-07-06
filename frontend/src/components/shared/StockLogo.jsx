import React from 'react';

/**
 * StockLogo — company brand mark with graceful fallback:
 *   brand favicon (DuckDuckGo) → Google favicon → 2-letter monogram on a
 *   deterministic gradient. Self-contained (inline styles) so it renders
 *   correctly on any page without importing a page stylesheet.
 *
 * Lifted from the inline `Logo` in DashboardV3 so the watchlist rail (and,
 * later, other surfaces) share one implementation.
 */
const TICKER_DOMAINS = {
  RELIANCE: 'ril.com', TCS: 'tcs.com', BAJFINANCE: 'bajajfinserv.in',
  INFY: 'infosys.com', HDFCBANK: 'hdfcbank.com', ICICIBANK: 'icicibank.com',
  BHARTIARTL: 'airtel.in', LT: 'larsentoubro.com', MARUTI: 'marutisuzuki.com',
  KOTAKBANK: 'kotak.com', ADANIENT: 'adanienterprises.com', SBIN: 'sbi.co.in',
  AXISBANK: 'axisbank.com', TATAPOWER: 'tatapower.com', POLYCAB: 'polycab.com',
  VOLTAS: 'voltas.com', CUMMINSIND: 'cummins.com', TITAN: 'titancompany.com',
  SUNPHARMA: 'sunpharma.com', DIVISLAB: 'divislabs.com', PERSISTENT: 'persistent.com',
  WIPRO: 'wipro.com', HINDUNILVR: 'hul.co.in', NESTLEIND: 'nestle.in',
  ONGC: 'ongcindia.com', NTPC: 'ntpc.co.in', POWERGRID: 'powergrid.in',
  COALINDIA: 'coalindia.in', IOC: 'iocl.com', BPCL: 'bharatpetroleum.in',
  GAIL: 'gailonline.com', ADANIGREEN: 'adanigreenenergy.com', TATASTEEL: 'tatasteel.com',
  JSWSTEEL: 'jsw.in', HINDALCO: 'hindalco.com', VEDL: 'vedantalimited.com',
  SBICARD: 'sbicard.com', BAJAJFINSV: 'bajajfinserv.in', HDFCLIFE: 'hdfclife.com',
  SBILIFE: 'sbilife.co.in', ICICIPRULI: 'iciciprulife.com', INDUSINDBK: 'indusind.com',
  PNB: 'pnbindia.in', BANKBARODA: 'bankofbaroda.in', CHOLAFIN: 'cholamandalam.com',
  HCLTECH: 'hcltech.com', TECHM: 'techmahindra.com', LTIM: 'ltimindtree.com',
  COFORGE: 'coforge.com', MPHASIS: 'mphasis.com', NETWORK18: 'network18online.com',
  ZEEL: 'zee.com', PVRINOX: 'pvrinox.com',
  TATAMOTORS: 'tatamotors.com', MM: 'mahindra.com', BAJAJ_AUTO: 'bajajauto.com',
  EICHERMOT: 'eichermotors.com', HEROMOTOCO: 'heromotocorp.com', TVSMOTOR: 'tvsmotor.com',
  ASHOKLEY: 'ashokleyland.com', BOSCHLTD: 'bosch.in',
  DRREDDY: 'drreddys.com', CIPLA: 'cipla.com', APOLLOHOSP: 'apollohospitals.com',
  AUROPHARMA: 'aurobindo.com', LUPIN: 'lupin.com', BIOCON: 'biocon.com',
  ITC: 'itcportal.com', BRITANNIA: 'britannia.co.in', DABUR: 'dabur.com',
  GODREJCP: 'godrejcp.com', TATACONSUM: 'tataconsumer.com', ASIANPAINT: 'asianpaints.com',
  PIDILITIND: 'pidilite.com', DMART: 'dmartindia.com', TRENT: 'trentlimited.com',
  ULTRACEMCO: 'ultratechcement.com', GRASIM: 'grasim.com', SHREECEM: 'shreecement.com',
  AMBUJACEM: 'ambujacement.com', ACC: 'acclimited.com', SIEMENS: 'siemens.co.in',
  ABB: 'abb.com', HAVELLS: 'havells.com', BEL: 'bel-india.in', BHEL: 'bhel.com',
};

export function tickerBg(sym) {
  let h = 0;
  for (const ch of (sym || '')) h = (h + ch.charCodeAt(0) * 13) % 360;
  return `linear-gradient(135deg, hsl(${h} 70% 56%) 0%, hsl(${(h + 38) % 360} 60% 42%) 100%)`;
}

export default function StockLogo({ sym, size = 28, radius = 8 }) {
  const domain = TICKER_DOMAINS[(sym || '').toUpperCase()];
  const sources = domain
    ? [`https://icons.duckduckgo.com/ip3/${domain}.ico`,
       `https://www.google.com/s2/favicons?domain=${domain}&sz=128`]
    : [];
  const [idx, setIdx] = React.useState(0);
  React.useEffect(() => { setIdx(0); }, [sym]);

  const base = {
    width: size, height: size, borderRadius: radius, flexShrink: 0,
    display: 'grid', placeItems: 'center', overflow: 'hidden',
  };

  if (idx >= sources.length) {
    return (
      <div style={{
        ...base, background: tickerBg(sym), color: '#fff', fontWeight: 700,
        fontSize: Math.round(size * 0.36), letterSpacing: '0.02em',
        boxShadow: '0 2px 6px rgba(0,0,0,0.30), inset 0 1px 0 rgba(255,255,255,0.18)',
      }}>
        {(sym || '??').slice(0, 2)}
      </div>
    );
  }
  return (
    <div style={{ ...base, background: '#fff', boxShadow: '0 2px 6px rgba(0,0,0,0.30), inset 0 0 0 1px rgba(255,255,255,0.5)' }}>
      <img
        src={sources[idx]}
        alt={sym}
        onError={() => setIdx((i) => i + 1)}
        style={{ width: '76%', height: '76%', objectFit: 'contain', display: 'block' }}
      />
    </div>
  );
}
