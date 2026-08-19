/* Nifty Satvik Terminal — parallel frontend (buildless).
   Fetches the live backend (/api/*) and falls back to bundled SAMPLE data on any
   failure, so the page always renders. Chart indicators (MA/RSI/MACD) are computed
   client-side from the /yahoo/historical candles. */
'use strict';
const CFG = window.NQ_CONFIG || { apiBase: '/api' };
const NF = (n, d = 2) => (n == null || isNaN(n)) ? '—'
  : Number(n).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
let USED_SAMPLE = false;

async function api(path) {
  try {
    const r = await fetch(CFG.apiBase + path, { credentials: 'include', headers: { Accept: 'application/json' } });
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) { return null; }
}

/* ---- SAMPLE fallback (real 2026-08-17 scan) ------------------------------- */
const CONAME = { MCX:'Multi Commodity Exchange', IKS:'Inventurus Knowledge', APLAPOLLO:'APL Apollo Tubes',
  ADANIPORTS:'Adani Ports & SEZ', CCL:'CCL Products (India)', HEG:'HEG Ltd', INDUSINDBK:'IndusInd Bank',
  NESTLEIND:'Nestlé India', CUB:'City Union Bank', 'BAJAJ-AUTO':'Bajaj Auto' };
const SAMPLE = {
  regime: { status:'BEAR', strength:39, breadth:-35, vix:14.2 },
  indices: [['NIFTY',24148,-0.82],['BANKNIFTY',51320,-1.14],['MIDCAP',56880,-0.61],['INDIA VIX',14.20,3.1],['BREADTH',-35,null],['REGIME','BEAR · 39',null]],
  buys: [
    {sym:'MCX',last:2961.0,chg:1.64,e:2961.0,s:2664.9,t:3553.2,ext:17.56,body:0.65,crs:0.144,conv:'norm',grade:'A'},
    {sym:'IKS',last:1835.0,chg:0.82,e:1835.0,s:1725.0,t:2055.0,ext:12.55,body:0.83,crs:0.143,conv:'norm',grade:'A'},
    {sym:'APLAPOLLO',last:2096.7,chg:-0.31,e:2096.7,s:1951.7,t:2386.7,ext:9.13,body:0.74,crs:0.090,conv:'norm',grade:'A'},
    {sym:'ADANIPORTS',last:1688.4,chg:0.44,e:1688.4,s:1640.4,t:1784.4,ext:6.84,body:0.16,crs:0.078,conv:'low',grade:'A'},
    {sym:'CCL',last:1135.0,chg:-0.14,e:1135.0,s:1116.2,t:1172.6,ext:8.07,body:0.16,crs:0.077,conv:'low',grade:'A'},
  ],
  holds: [
    {sym:'HEG',qty:766,avg:653.0,last:704.6,chg:0.51,s:587.7,t:783.6,pnl:7.90},
    {sym:'INDUSINDBK',qty:206,avg:968.0,last:1013.4,chg:0.72,s:908.1,t:1087.8,pnl:4.69},
    {sym:'NESTLEIND',qty:138,avg:1450.13,last:1480.3,chg:0.19,s:1374.89,t:1600.61,pnl:2.08},
    {sym:'MCX',qty:67,avg:2913.1,last:2961.0,chg:1.64,s:2621.79,t:3495.72,pnl:1.64},
    {sym:'CUB',qty:950,avg:210.03,last:210.47,chg:-0.24,s:197.35,t:235.39,pnl:0.21},
  ],
  sell: { ticker:'BAJAJ-AUTO', headline:'+2R target reached — trim 40%', partial_pct:40, last:11607, level:10669 },
  nav: [1000000,1003200,1008900,1006100,1012400,1017800,1014200,1021600,1026900,1023400,1029700,1031025,1027800,1030100,1024600,1026900,1021300,1023800,1018400,1021700,1017200,1020600,1016900,1019489],
};

/* ---- normalizers (defensive — backend shapes vary) ----------------------- */
const num = v => (typeof v === 'number' ? v : parseFloat(v));
function normSignals(j) {
  if (!j || !Array.isArray(j.signals)) return null;
  const buys = [], holds = [];
  for (const s of j.signals) {
    const sym = s.ticker || s.symbol; if (!sym) continue;
    const base = { sym, last: num(s.current_price ?? s.close ?? s.entry), chg: num(s.chg_pct ?? 0) || 0,
      e: num(s.entry), s: num(s.stop), t: num(s.target), ext: num(s.ext_pct_over_sma44),
      body: num(s.body_ratio), crs: num(s.crs_rank), conv: (s.signal_conviction === 'low' ? 'low' : 'norm'),
      grade: s.grade || 'A', sell: s.sell_guidance || null };
    if ((s.status || '').toUpperCase() === 'FRESH') buys.push(base); else holds.push(base);
  }
  return { buys, holds, regime: j.regime || null, portfolio: j.portfolio || null };
}
function normPositions(j) {
  const arr = Array.isArray(j) ? j : (j && j.positions) || null;
  if (!arr) return null;
  return arr.map(p => ({ sym: p.ticker || p.symbol, qty: num(p.held_qty ?? p.qty ?? p.nq_recorded_qty),
    avg: num(p.avg_fill_price ?? p.entry ?? p.avg), last: num(p.last_price ?? p.current_price),
    pnl: num(p.pnl_pct ?? 0) || 0, s: num(p.stop), t: num(p.target),
    sell: p.sell_guidance || null, statusUser: p.status_for_user })).filter(p => p.sym);
}
function normNav(j) {
  const h = j && j.history; if (!Array.isArray(h) || !h.length) return null;
  return h.map(r => num(r.value ?? r.nav)).filter(v => !isNaN(v));
}
function normIndices(j) {
  const arr = Array.isArray(j) ? j : (j && (j.indices || j.data)) || null;
  if (!arr || !arr.length) return null;
  return arr.map(x => [x.name || x.symbol || x.label, num(x.ltp ?? x.last ?? x.price ?? x.value),
    num(x.change_pct ?? x.changePct ?? x.chg_pct ?? x.change)]);
}
function normCandles(j) {
  if (!Array.isArray(j) || j.length < 5) return null;
  return j.map(r => Array.isArray(r)
    ? { date: String(r[0]).slice(0, 10), o: +r[1], h: +r[2], l: +r[3], c: +r[4], v: +r[5] }
    : { date: String(r.date || r.Date).slice(0, 10), o: +(r.open ?? r.o), h: +(r.high ?? r.h), l: +(r.low ?? r.l), c: +(r.close ?? r.c), v: +(r.volume ?? r.v ?? 0) });
}

/* ---- state --------------------------------------------------------------- */
const S = { buys: [], holds: [], regime: {}, indices: [], nav: [], sell: null, portfolio: null };
let G = null, CUR = null, SUB = 'RSI', PERIOD = CFG.candlePeriod, candleCache = {};

async function boot() {
  const [sig, pos, nav, idx, sell] = await Promise.all([
    api('/signals'), api('/positions/nq'), api('/portfolio/nav-history?days=' + (CFG.navHistoryDays||365)),
    api('/yahoo/index-sparklines'), api('/signals/sell-guidance'),
  ]);
  const ns = normSignals(sig), np = normPositions(pos), nn = normNav(nav), ni = normIndices(idx);
  const anyLive = !!(ns || np || nn || ni);
  USED_SAMPLE = !anyLive;

  S.buys = (ns && ns.buys.length ? ns.buys : SAMPLE.buys);
  S.holds = (np && np.length ? np : (ns && ns.holds.length ? ns.holds : SAMPLE.holds));
  S.regime = (ns && ns.regime) || SAMPLE.regime;
  S.indices = ni || SAMPLE.indices;
  S.nav = nn || SAMPLE.nav;
  S.portfolio = (ns && ns.portfolio) || null;
  S.sell = (sell && sell.positions && sell.positions[0]) ? {
    ticker: sell.positions[0].ticker, headline: (sell.positions[0].sell_guidance||{}).headline || 'Take profit',
    partial_pct: (sell.positions[0].sell_guidance||{}).partial_pct, last: sell.positions[0].last_price,
    level: (sell.positions[0].sell_guidance||{}).suggested_exit_price } : SAMPLE.sell;

  renderChrome(); renderWatchlist(); renderPositions(); renderNavSpark(); renderSell(); renderFoot();
  select((S.buys[0] || S.holds[0]).sym);
}

/* ---- render -------------------------------------------------------------- */
function bookFor(sym) {
  const b = S.buys.find(x => x.sym === sym);
  if (b) return { ...b, kind: 'buy', co: CONAME[sym] || sym };
  const h = S.holds.find(x => x.sym === sym);
  if (h) return { ...h, kind: 'hold', co: CONAME[sym] || sym, e: h.avg };
  return { sym, kind: 'buy', co: sym, last: 0 };
}
function renderChrome() {
  document.getElementById('idx').innerHTML = S.indices.map(x =>
    `<div class="ix"><span class="k">${x[0]}</span><span class="v n">${typeof x[1]==='number'?NF(x[1],x[1]>1000?0:2):x[1]}${x[2]!=null?`<small class="${x[2]>=0?'up':'dn'}">${x[2]>=0?'▲':'▼'}${Math.abs(x[2]).toFixed(2)}%</small>`:''}</span></div>`).join('');
  const nav = S.nav[S.nav.length-1], ret = S.nav.length>1 ? (nav/S.nav[0]-1)*100 : 0;
  document.getElementById('acctNav').innerHTML = `₹${NF(nav,0)} <span class="${ret>=0?'up':'dn'}" style="font-size:12px">${ret>=0?'▲':'▼'}${Math.abs(ret).toFixed(2)}%</span>`;
  const bad = document.getElementById('srcBadge');
  bad.textContent = USED_SAMPLE ? 'SAMPLE' : 'LIVE'; bad.className = 'src ' + (USED_SAMPLE ? 'sample' : 'live');
  bad.title = USED_SAMPLE ? 'Backend unreachable / not logged in — showing bundled sample data' : 'Live data from the backend';
}
function wlRows(el, list, kind) {
  document.getElementById(el).innerHTML = list.map(x => {
    const dot = kind==='hold' ? 'h' : (x.conv==='low' ? 'l' : 'n');
    return `<div class="r" data-s="${x.sym}"><div class="c sym"><span class="cdot ${dot}"></span>${x.sym}</div><div class="c last n">${NF(x.last)}</div><div class="c chg ${(x.chg||0)>=0?'up':'dn'}">${(x.chg||0)>=0?'+':''}${(x.chg||0).toFixed(2)}%</div></div>`;
  }).join('');
}
function renderWatchlist() {
  wlRows('wlBuys', S.buys, 'buy'); wlRows('wlHolds', S.holds, 'hold');
  document.querySelectorAll('.wl .r').forEach(r => r.addEventListener('click', () => select(r.dataset.s)));
}
function renderPositions() {
  const rows = S.holds.map(h => {
    const mv = h.qty*h.last, gain = (h.last-h.avg)*h.qty, toT = h.t>h.s ? (h.last-h.s)/(h.t-h.s)*100 : 0;
    return `<tr data-s="${h.sym}"><td><span class="psym"><span class="cdot h"></span>${h.sym}</span></td>
      <td class="n">${h.qty}</td><td class="n">${NF(h.avg)}</td><td class="n">${NF(h.last)}</td>
      <td class="n">₹${NF(mv,0)}</td><td class="n ${gain>=0?'up':'dn'}">${gain>=0?'+':''}₹${NF(gain,0)}</td>
      <td class="n ${h.pnl>=0?'up':'dn'}">${h.pnl>=0?'+':''}${(h.pnl||0).toFixed(2)}%</td>
      <td class="barcell"><div class="tgbar"><i style="width:${Math.max(0,Math.min(100,toT)).toFixed(0)}%"></i></div></td></tr>`;
  }).join('');
  document.getElementById('pos').innerHTML = rows;
  const totMv = S.holds.reduce((a,h)=>a+h.qty*h.last,0);
  document.getElementById('posMeta').innerHTML = `${S.holds.length} open · ₹${NF(totMv,0)}`;
  document.querySelectorAll('#pos tr').forEach(r => r.addEventListener('click', () => select(r.dataset.s)));
}
function renderSell() {
  const p = document.getElementById('tpPanel'); if (!S.sell) { p.style.display='none'; return; }
  p.style.display='block';
  document.getElementById('tpBody').innerHTML =
    `<div class="note"><b>${S.sell.ticker}</b> ${S.sell.headline}${S.sell.level?` (₹${NF(S.sell.level,0)})`:''}. Resting limit should fill.</div>
     <button class="place s" style="margin-top:10px">Sell ${S.sell.partial_pct?S.sell.partial_pct+'%':''} · ${S.sell.ticker}</button>`;
}
function renderNavSpark() {
  const v = S.nav; if (!v || v.length<2) return;
  const svg = document.getElementById('navspark'), w = svg.clientWidth||280, h = 96, mn = Math.min(...v), mx = Math.max(...v), sp = mx-mn||1;
  const X = i => i*w/(v.length-1), Y = x => 6+(1-(x-mn)/sp)*(h-12);
  const line = v.map((x,i)=>(i?'L':'M')+X(i).toFixed(1)+' '+Y(x).toFixed(1)).join(' ');
  const up = v[v.length-1]>=v[0], col = up?'#26c281':'#f6465d';
  svg.setAttribute('viewBox',`0 0 ${w} ${h}`); svg.setAttribute('preserveAspectRatio','none');
  svg.innerHTML = `<defs><linearGradient id="ng" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${col}" stop-opacity=".2"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
    <path d="${line} L ${w} ${h} L 0 ${h} Z" fill="url(#ng)"/><path d="${line}" fill="none" stroke="${col}" stroke-width="1.8"/>`;
  const ret = (v[v.length-1]/v[0]-1)*100;
  document.getElementById('navMeta').innerHTML = `<span>₹${NF(v[0],0)}</span><span class="${ret>=0?'up':'dn'}">${ret>=0?'+':''}${ret.toFixed(2)}%</span><span>₹${NF(v[v.length-1],0)}</span>`;
}
function renderFoot() {
  document.getElementById('foot').innerHTML =
    `<span>weekly-swing-0094-rank-P</span><span>DSR 0.89 · not certified</span><span>fills self-reported</span><span>${USED_SAMPLE?'sample data — backend not connected':'live · /api'}</span>`;
}

/* ---- chart --------------------------------------------------------------- */
const maN = (a,p) => a.map((_,i)=>{const st=Math.max(0,i-p+1),sg=a.slice(st,i+1);return sg.reduce((x,y)=>x+y,0)/sg.length;});
function synthCandles(sym) {
  const bk = bookFor(sym), f = bk.last || 1000, ph = (sym.charCodeAt(0)%7);
  const SHAPE=[1780,1815,1795,1860,1930,1895,1985,2060,2015,2130,2205,2185,2290,2360,2320,2430,2515,2485,2595,2690,2645,2795,2905,2865,3015,3125,3185,3095,3215,3155,3045,2961].map(x=>x/2961);
  const base=new Date(2025,7,1), out=[];
  SHAPE.forEach((r,i)=>{const c=+(f*r*(1+0.017*Math.sin(i*1.05+ph))).toFixed(2);const o=i?out[i-1].c:c*0.99;
    const hi=Math.max(o,c)*(1+0.009+0.006*Math.abs(Math.sin(i*1.3+ph))),lo=Math.min(o,c)*(1-0.009-0.006*Math.abs(Math.cos(i*1.1+ph)));
    const d=new Date(base);d.setDate(d.getDate()+i*7);
    out.push({date:d.toISOString().slice(0,10),o:+o.toFixed(2),h:+hi.toFixed(2),l:+lo.toFixed(2),c,v:Math.round((0.6+0.9*Math.abs(Math.sin(i*0.8+ph)))*1e6)});});
  out[out.length-1].c=f; return out;
}
async function candlesFor(sym) {
  if (candleCache[sym+PERIOD]) return candleCache[sym+PERIOD];
  const raw = await api(`/yahoo/historical/${encodeURIComponent(sym)}?interval=${CFG.candleInterval||'1wk'}&period=${PERIOD}&exchange=NSE`);
  const c = normCandles(raw) || synthCandles(sym);
  candleCache[sym+PERIOD] = c; return c;
}
function fmtD(s){const d=new Date(s);return d.getDate()+' '+['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()]+" '"+String(d.getFullYear()).slice(2);}

function drawChart(cd, lv) {
  const closes = cd.map(x => x.c), n = cd.length;
  const ma10=maN(closes,10),ma20=maN(closes,20),ma44=maN(closes,44);
  const vols=cd.map(x=>+(x.v/1e6).toFixed(2)),volMA=maN(vols,10);
  const rsi=(()=>{const p=14,o=[null];let ag=0,al=0;for(let i=1;i<n;i++){const dd=closes[i]-closes[i-1],g=Math.max(dd,0),l=Math.max(-dd,0);
    if(i<p){ag+=g;al+=l;o[i]=null;}else if(i===p){ag=(ag+g)/p;al=(al+l)/p;o[i]=100-100/(1+(al?ag/al:100));}
    else{ag=(ag*(p-1)+g)/p;al=(al*(p-1)+l)/p;o[i]=100-100/(1+(al?ag/al:100));}}return o;})();
  const ema=(a,p)=>{const k=2/(p+1),o=[];a.forEach((v,i)=>o[i]=i?v*k+o[i-1]*(1-k):v);return o;};
  const e12=ema(closes,12),e26=ema(closes,26),macdL=closes.map((_,i)=>e12[i]-e26[i]),sigL=ema(macdL,9),histL=macdL.map((m,i)=>m-sigL[i]);

  const svg=document.getElementById('kchart');
  const W=Math.round(svg.clientWidth)||660,H=Math.round(svg.clientHeight)||432,padR=58,padT=10;
  const priceH=Math.round(H*0.56),volTop=padT+priceH+8,volH=Math.round(H*0.13),
        rsiTop=volTop+volH+14,rsiH=Math.round(H*0.16),axisY=H-4;
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  const lows=cd.map(x=>x.l).concat(lv.s?[lv.s]:[]),highs=cd.map(x=>x.h).concat(lv.t?[lv.t]:[]);
  const pmin=Math.min(...lows)*0.998,pmax=Math.max(...highs)*1.002,pr=pmax-pmin;
  const Y=p=>padT+(1-(p-pmin)/pr)*priceH,cw=(W-padR)/n,bw=Math.min(13,cw*0.62);
  const vmax=Math.max(...cd.map(x=>x.v))||1;
  let grid='',axis='';const tk=5;
  for(let g=0;g<=tk;g++){const p=pmin+pr*g/tk,y=Y(p);grid+=`<line x1="0" y1="${y}" x2="${W-padR}" y2="${y}" stroke="#141821"/>`;
    axis+=`<text x="${W-padR+6}" y="${y+3}" fill="#69707f" font-size="10">${Math.round(p).toLocaleString('en-IN')}</text>`;}
  let bars='',wicks='',vol='',dax='';const step=Math.max(1,Math.round(n/7));
  cd.forEach((x,i)=>{const cx=i*cw+cw/2,up=x.c>=x.o,col=up?'#26c281':'#f6465d';
    wicks+=`<line x1="${cx}" y1="${Y(x.h)}" x2="${cx}" y2="${Y(x.l)}" stroke="${col}" stroke-width="1"/>`;
    const yo=Y(x.o),yc=Y(x.c),tp=Math.min(yo,yc),hh=Math.max(1.4,Math.abs(yo-yc));
    bars+=`<rect x="${cx-bw/2}" y="${tp}" width="${bw}" height="${hh}" fill="${col}"/>`;
    vol+=`<rect x="${cx-bw/2}" y="${volTop+volH-(x.v/vmax)*volH}" width="${bw}" height="${(x.v/vmax)*volH}" fill="${col}" opacity=".45"/>`;
    if(i%step===0||i===n-1)dax+=`<text x="${cx}" y="${axisY}" fill="#69707f" font-size="10" text-anchor="middle">${fmtD(x.date)}</text>`;});
  const mpath=arr=>arr.map((m,i)=>(i?'L':'M')+(i*cw+cw/2).toFixed(1)+' '+Y(m).toFixed(1)).join(' ');
  const maSvg=[[ma10,'#e8a13a'],[ma20,'#4d9fff'],[ma44,'#b06fe8']].map(([a,c])=>`<path d="${mpath(a)}" fill="none" stroke="${c}" stroke-width="1.3" opacity=".92"/>`).join('');
  const vmaxD=Math.max(...vols),vY=v=>volTop+volH-(v/vmaxD)*volH;
  const volMApath=volMA.map((v,i)=>(i?'L':'M')+(i*cw+cw/2).toFixed(1)+' '+vY(v).toFixed(1)).join(' ');
  // RSI pane
  const RY=v=>rsiTop+(1-v/100)*rsiH;let rsiGrid='',rsiAx='',rsiPath='',rst=false;
  [75,50,35].forEach(l=>{rsiGrid+=`<line x1="0" y1="${RY(l)}" x2="${W-padR}" y2="${RY(l)}" stroke="${l===50?'#242938':'#3a2f4a'}" stroke-width="1" stroke-dasharray="${l===50?'2 5':'4 4'}"/>`;
    if(l!==50)rsiAx+=`<text x="${W-padR+6}" y="${RY(l)+3}" fill="#69707f" font-size="9">${l}</text>`;});
  rsi.forEach((v,i)=>{if(v==null)return;rsiPath+=(rst?'L':'M')+(i*cw+cw/2).toFixed(1)+' '+RY(v).toFixed(1)+' ';rst=true;});
  const rsiPane=`<line x1="0" y1="${rsiTop-9}" x2="${W-padR}" y2="${rsiTop-9}" stroke="#1d212b"/>${rsiGrid}<path d="${rsiPath}" fill="none" stroke="#b58aff" stroke-width="1.4"/>${rsiAx}<text x="4" y="${rsiTop+11}" fill="#8a92a3" font-size="10" font-weight="600">RSI(14) · 75 / 35</text>`;
  // MACD pane
  const mAbs=Math.max(...macdL.map(Math.abs),...sigL.map(Math.abs),...histL.map(Math.abs))||1;
  const mCen=rsiTop+rsiH/2,MY=v=>mCen-(v/mAbs)*(rsiH/2*0.86),y0=MY(0);let mHist='';
  histL.forEach((h,i)=>{const cx=i*cw+cw/2,y=MY(h);mHist+=`<rect x="${cx-bw/2}" y="${Math.min(y0,y)}" width="${bw}" height="${Math.max(1,Math.abs(y-y0))}" fill="${h>=0?'#26c281':'#f6465d'}" opacity=".5"/>`;});
  const macdPane=`<line x1="0" y1="${rsiTop-9}" x2="${W-padR}" y2="${rsiTop-9}" stroke="#1d212b"/><line x1="0" y1="${y0}" x2="${W-padR}" y2="${y0}" stroke="#242938" stroke-width="1" stroke-dasharray="2 5"/>${mHist}<path d="${mpath(macdL)}" fill="none" stroke="#4d9fff" stroke-width="1.3"/><path d="${mpath(sigL)}" fill="none" stroke="#e8a13a" stroke-width="1.3"/><text x="4" y="${rsiTop+11}" fill="#8a92a3" font-size="10" font-weight="600">MACD(12,26,9)</text>`;
  const subPane=SUB==='RSI'?rsiPane:macdPane;
  // levels + last
  const levels=[[lv.e,'#3b76f0'],[lv.s,'#f6465d'],[lv.t,'#26c281']].filter(x=>x[0]).map(([p,c])=>
    `<line x1="0" y1="${Y(p)}" x2="${W-padR}" y2="${Y(p)}" stroke="${c}" stroke-width="1" stroke-dasharray="4 4" opacity=".75"/><rect x="${W-padR}" y="${Y(p)-8}" width="${padR}" height="16" fill="${c}"/><text x="${W-padR+5}" y="${Y(p)+3}" fill="#05130c" font-size="10" font-weight="700">${Math.round(p).toLocaleString('en-IN')}</text>`).join('');
  const lastP=closes[n-1],ly=Y(lastP);
  const lastTag=`<line x1="0" y1="${ly}" x2="${W-padR}" y2="${ly}" stroke="#e4e7ee" stroke-width="1" stroke-dasharray="1 3" opacity=".5"/><rect x="${W-padR}" y="${ly-8}" width="${padR}" height="16" fill="#2b3140"/><text x="${W-padR+5}" y="${ly+3}" fill="#e4e7ee" font-size="10" font-weight="700">${NF(lastP)}</text>`;
  svg.innerHTML=`${grid}<line x1="0" y1="${volTop-6}" x2="${W-padR}" y2="${volTop-6}" stroke="#1d212b"/>${vol}
    <path d="${volMApath}" fill="none" stroke="#8a92a3" stroke-width="1" opacity=".65"/>${wicks}${bars}${maSvg}${subPane}
    ${levels}${lastTag}${axis}${dax}
    <g id="cx" style="opacity:0"><line id="cxv" y1="${padT}" y2="${rsiTop+rsiH}" stroke="#8a92a3" stroke-width="1" stroke-dasharray="2 3"/>
      <line id="cxh" x1="0" x2="${W-padR}" stroke="#8a92a3" stroke-width="1" stroke-dasharray="2 3"/>
      <rect id="cxpb" x="${W-padR}" width="${padR}" height="16" fill="#3b76f0"/><text id="cxpt" x="${W-padR+5}" fill="#fff" font-size="10" font-weight="700"></text></g>`;
  G={W,H,padR,padT,priceH,pmin,pr,cw,n,cd,closes,Y,ma10,ma20,ma44,vols,rsi,macd:{l:macdL,s:sigL}};
  document.getElementById('legend').innerHTML=legendFor(n-1);
}
function legendFor(i){if(!G)return'';
  const sub=SUB==='RSI'?`<span style="color:#b58aff">RSI <b>${G.rsi[i]!=null?G.rsi[i].toFixed(1):'—'}</b></span>`
    :`<span style="color:#4d9fff">MACD <b>${G.macd.l[i].toFixed(2)}</b></span><span style="color:#e8a13a">SIG <b>${G.macd.s[i].toFixed(2)}</b></span>`;
  return `<span style="color:#e8a13a">MA10 <b>${NF(G.ma10[i],0)}</b></span><span style="color:#4d9fff">MA20 <b>${NF(G.ma20[i],0)}</b></span><span style="color:#b06fe8">MA44 <b>${NF(G.ma44[i],0)}</b></span><span>Vol <b style="color:var(--ink-2)">${G.vols[i].toFixed(2)}M</b></span>`+sub;
}

/* ---- order / detail panel ----------------------------------------------- */
function drawOrder(sym) {
  const d = bookFor(sym);
  document.getElementById('odTitle').textContent = (d.kind==='buy'?'Order · ':'Position · ')+sym;
  if (d.kind==='buy') {
    const R=d.e-d.s,risk=d.e?R/d.e*100:0,low=d.conv==='low',qty=Math.floor(200000/(d.e||1));
    document.getElementById('od').innerHTML=`
      <div class="side"><b class="buy on">Buy</b><b>Sell</b></div>
      <div class="oi"><span class="k">Limit price</span><span class="v">₹${NF(d.e)}</span></div>
      <div class="oi"><span class="k">Quantity</span><span class="v">${qty} sh</span></div>
      <div class="oi"><span class="k">Est. cost</span><span class="v">₹${NF(qty*d.e,0)}</span></div>
      <div class="kv"><span class="k">Stop loss</span><span class="v dn">₹${NF(d.s)}</span></div>
      <div class="kv"><span class="k">Target · +2R</span><span class="v up">₹${NF(d.t)}</span></div>
      <div class="rrline"><i class="r" style="width:33.3%"></i><i class="g" style="width:66.7%"></i></div>
      <div class="kv"><span class="k">Risk / R:R</span><span class="v">${risk.toFixed(2)}% · 1:2</span></div>
      <div class="kv"><span class="k">Ext / body / CRS</span><span class="v">${d.ext!=null?d.ext:'—'}% · ${d.body!=null?d.body:'—'} · ${d.crs!=null?Number(d.crs).toFixed(3):'—'}</span></div>
      <div class="kv"><span class="k">Grade · conviction</span><span class="v"><span class="tag A">${d.grade||'A'}</span> <span class="tag ${low?'low':'norm'}">${low?'Low':'Normal'}</span></span></div>
      <button class="place b">Buy ${sym}</button>`;
  } else {
    const mv=d.qty*d.last,gain=(d.last-d.avg)*d.qty,toT=d.t>d.s?(d.last-d.s)/(d.t-d.s)*100:0;
    document.getElementById('od').innerHTML=`
      <div class="oi"><span class="k">Qty · avg</span><span class="v">${d.qty} · ₹${NF(d.avg)}</span></div>
      <div class="oi"><span class="k">Market value</span><span class="v">₹${NF(mv,0)}</span></div>
      <div class="oi"><span class="k">Unrealized P&L</span><span class="v ${gain>=0?'up':'dn'}">${gain>=0?'+':''}₹${NF(gain,0)} · ${(d.pnl||0).toFixed(2)}%</span></div>
      <div class="kv"><span class="k">Stop</span><span class="v dn">₹${NF(d.s)}</span></div>
      <div class="kv"><span class="k">Target · +2R</span><span class="v up">₹${NF(d.t)}</span></div>
      <div class="rrline"><i class="g" style="width:${Math.max(0,Math.min(100,toT)).toFixed(0)}%"></i><i style="flex:1;background:#171b23"></i></div>
      <div class="kv"><span class="k">Progress to target</span><span class="v">${toT.toFixed(0)}%</span></div>
      <div class="kv"><span class="k">Exit plan</span><span class="v" style="font-weight:500;color:var(--ink-2);font-size:12px">40% @2R · 40% blow-off · 20% runner</span></div>
      <button class="place b" style="background:var(--raise);color:var(--ink-2)">Manage exit</button>`;
  }
}

/* ---- select + interactivity --------------------------------------------- */
async function select(sym) {
  CUR = sym; const d = bookFor(sym);
  document.getElementById('cTk').textContent = sym;
  document.getElementById('cCo').textContent = d.co;
  document.getElementById('cPx').textContent = NF(d.last);
  const ce=document.getElementById('cChg');ce.textContent=(d.chg>=0?'+':'')+(d.chg||0).toFixed(2)+'%';ce.className='pchg n '+((d.chg||0)>=0?'up':'dn');
  document.querySelectorAll('.wl .r').forEach(r=>r.classList.toggle('sel',r.dataset.s===sym));
  drawOrder(sym);
  const cd = await candlesFor(sym);
  drawChart(cd, { e:d.e, s:d.s, t:d.t });
}
document.getElementById('subtog').querySelectorAll('b').forEach(b=>b.addEventListener('click',()=>{
  SUB=b.dataset.sub;document.querySelectorAll('#subtog b').forEach(x=>x.classList.toggle('on',x===b));
  if(CUR)candlesFor(CUR).then(cd=>{const d=bookFor(CUR);drawChart(cd,{e:d.e,s:d.s,t:d.t});});
}));
document.getElementById('tf').querySelectorAll('b').forEach(b=>b.addEventListener('click',()=>{
  PERIOD=b.dataset.tf.toLowerCase();document.querySelectorAll('#tf b').forEach(x=>x.classList.toggle('on',x===b));
  if(CUR)select(CUR);
}));
// crosshair
const cwrap=document.getElementById('cwrap'),tip=document.getElementById('tip');
cwrap.addEventListener('mousemove',e=>{if(!G)return;const rect=cwrap.getBoundingClientRect();
  const mx=(e.clientX-rect.left)/rect.width*G.W,my=(e.clientY-rect.top)/rect.height*G.H;
  if(mx>G.W-G.padR){hideCx();return;}
  const i=Math.max(0,Math.min(G.n-1,Math.round((mx-G.cw/2)/G.cw))),cx=i*G.cw+G.cw/2,o=G.cd[i];
  const g=document.getElementById('cx');g.style.opacity=1;
  document.getElementById('cxv').setAttribute('x1',cx);document.getElementById('cxv').setAttribute('x2',cx);
  const yy=Math.max(G.padT,Math.min(G.priceH+G.padT,my));
  document.getElementById('cxh').setAttribute('y1',yy);document.getElementById('cxh').setAttribute('y2',yy);
  const price=G.pmin+(1-(yy-G.padT)/G.priceH)*G.pr;
  document.getElementById('cxpb').setAttribute('y',yy-8);const pt=document.getElementById('cxpt');pt.setAttribute('y',yy+3);pt.textContent=NF(price);
  document.getElementById('legend').innerHTML=legendFor(i);
  const up=o.c>=o.o,chg=i?((o.c/G.closes[i-1]-1)*100):0;
  tip.style.opacity=1;
  tip.innerHTML=`<div class="d">${fmtD(o.date)}</div>
    <div class="g"><span>O</span><span class="n">${NF(o.o)}</span></div>
    <div class="g"><span>H</span><span class="n up">${NF(o.h)}</span></div>
    <div class="g"><span>L</span><span class="n dn">${NF(o.l)}</span></div>
    <div class="g"><span>C</span><span class="n ${up?'up':'dn'}">${NF(o.c)} <small style="opacity:.8">${chg>=0?'+':''}${chg.toFixed(2)}%</small></span></div>
    <div class="g" style="border-top:1px solid var(--line);margin-top:3px;padding-top:4px"><span>Vol</span><span class="n" style="color:var(--ink-2)">${G.vols[i].toFixed(2)}M</span></div>
    ${SUB==='RSI'?`<div class="g"><span>RSI</span><span class="n" style="color:#b58aff">${G.rsi[i]!=null?G.rsi[i].toFixed(1):'—'}</span></div>`
      :`<div class="g"><span>MACD</span><span class="n" style="color:#4d9fff">${G.macd.l[i].toFixed(2)}</span></div><div class="g"><span>Signal</span><span class="n" style="color:#e8a13a">${G.macd.s[i].toFixed(2)}</span></div>`}`;
});
function hideCx(){const g=document.getElementById('cx');if(g)g.style.opacity=0;tip.style.opacity=0;if(G)document.getElementById('legend').innerHTML=legendFor(G.n-1);}
cwrap.addEventListener('mouseleave',hideCx);
window.addEventListener('resize',()=>{if(CUR)candlesFor(CUR).then(cd=>{const d=bookFor(CUR);drawChart(cd,{e:d.e,s:d.s,t:d.t});});renderNavSpark();});

boot();
