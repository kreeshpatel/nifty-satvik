// Kite Stock Service — instrument search, caching, technical indicator calculations
// All stock page data flows through Kite API, not local mock data.

import { kiteInstruments, kiteHistorical, kiteLTP } from '@/services/api';

// ─── Instrument cache ───
let instrumentCache = null;
let cacheTimestamp = 0;
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 hours

// Well-known NSE stocks with tokens and names (fallback when backend is down)
const COMMON_STOCKS = [
  { tradingsymbol: 'RELIANCE', name: 'Reliance Industries Ltd', instrument_token: 738561, exchange: 'NSE' },
  { tradingsymbol: 'HDFCBANK', name: 'HDFC Bank Ltd', instrument_token: 341249, exchange: 'NSE' },
  { tradingsymbol: 'INFY', name: 'Infosys Ltd', instrument_token: 408065, exchange: 'NSE' },
  { tradingsymbol: 'TCS', name: 'Tata Consultancy Services Ltd', instrument_token: 2953217, exchange: 'NSE' },
  { tradingsymbol: 'ICICIBANK', name: 'ICICI Bank Ltd', instrument_token: 1270529, exchange: 'NSE' },
  { tradingsymbol: 'BAJFINANCE', name: 'Bajaj Finance Ltd', instrument_token: 81153, exchange: 'NSE' },
  { tradingsymbol: 'TATAMOTORS', name: 'Tata Motors Ltd', instrument_token: 884737, exchange: 'NSE' },
  { tradingsymbol: 'SBIN', name: 'State Bank of India', instrument_token: 779521, exchange: 'NSE' },
  { tradingsymbol: 'ADANIENT', name: 'Adani Enterprises Ltd', instrument_token: 6401, exchange: 'NSE' },
  { tradingsymbol: 'WIPRO', name: 'Wipro Ltd', instrument_token: 969473, exchange: 'NSE' },
  { tradingsymbol: 'MARUTI', name: 'Maruti Suzuki India Ltd', instrument_token: 2815745, exchange: 'NSE' },
  { tradingsymbol: 'TATASTEEL', name: 'Tata Steel Ltd', instrument_token: 895745, exchange: 'NSE' },
  { tradingsymbol: 'SUNPHARMA', name: 'Sun Pharmaceutical Industries', instrument_token: 857857, exchange: 'NSE' },
  { tradingsymbol: 'HCLTECH', name: 'HCL Technologies Ltd', instrument_token: 1850625, exchange: 'NSE' },
  { tradingsymbol: 'AXISBANK', name: 'Axis Bank Ltd', instrument_token: 1510401, exchange: 'NSE' },
  { tradingsymbol: 'KOTAKBANK', name: 'Kotak Mahindra Bank Ltd', instrument_token: 492033, exchange: 'NSE' },
  { tradingsymbol: 'LT', name: 'Larsen & Toubro Ltd', instrument_token: 2939649, exchange: 'NSE' },
  { tradingsymbol: 'BHARTIARTL', name: 'Bharti Airtel Ltd', instrument_token: 2714625, exchange: 'NSE' },
  { tradingsymbol: 'ASIANPAINT', name: 'Asian Paints Ltd', instrument_token: 60417, exchange: 'NSE' },
  { tradingsymbol: 'ULTRACEMCO', name: 'UltraTech Cement Ltd', instrument_token: 2952193, exchange: 'NSE' },
  { tradingsymbol: 'HINDUNILVR', name: 'Hindustan Unilever Ltd', instrument_token: 356865, exchange: 'NSE' },
  { tradingsymbol: 'ITC', name: 'ITC Ltd', instrument_token: 424961, exchange: 'NSE' },
  { tradingsymbol: 'NESTLEIND', name: 'Nestle India Ltd', instrument_token: 4598529, exchange: 'NSE' },
  { tradingsymbol: 'ONGC', name: 'Oil & Natural Gas Corporation', instrument_token: 633601, exchange: 'NSE' },
  { tradingsymbol: 'POWERGRID', name: 'Power Grid Corporation', instrument_token: 3834113, exchange: 'NSE' },
  { tradingsymbol: 'NTPC', name: 'NTPC Ltd', instrument_token: 2977281, exchange: 'NSE' },
  { tradingsymbol: 'JSWSTEEL', name: 'JSW Steel Ltd', instrument_token: 3001089, exchange: 'NSE' },
  { tradingsymbol: 'TECHM', name: 'Tech Mahindra Ltd', instrument_token: 3465729, exchange: 'NSE' },
  { tradingsymbol: 'DRREDDY', name: "Dr Reddy's Laboratories", instrument_token: 225537, exchange: 'NSE' },
  { tradingsymbol: 'CIPLA', name: 'Cipla Ltd', instrument_token: 177665, exchange: 'NSE' },
  { tradingsymbol: 'COALINDIA', name: 'Coal India Ltd', instrument_token: 5215745, exchange: 'NSE' },
  { tradingsymbol: 'BPCL', name: 'Bharat Petroleum Corporation', instrument_token: 134657, exchange: 'NSE' },
  { tradingsymbol: 'GRASIM', name: 'Grasim Industries Ltd', instrument_token: 315393, exchange: 'NSE' },
  { tradingsymbol: 'DIVISLAB', name: "Divi's Laboratories Ltd", instrument_token: 2800641, exchange: 'NSE' },
  { tradingsymbol: 'TITAN', name: 'Titan Company Ltd', instrument_token: 897537, exchange: 'NSE' },
  { tradingsymbol: 'EICHERMOT', name: 'Eicher Motors Ltd', instrument_token: 232961, exchange: 'NSE' },
  { tradingsymbol: 'BAJAJFINSV', name: 'Bajaj Finserv Ltd', instrument_token: 4268801, exchange: 'NSE' },
  { tradingsymbol: 'HEROMOTOCO', name: 'Hero MotoCorp Ltd', instrument_token: 345089, exchange: 'NSE' },
  { tradingsymbol: 'HINDALCO', name: 'Hindalco Industries Ltd', instrument_token: 348929, exchange: 'NSE' },
  { tradingsymbol: 'VEDL', name: 'Vedanta Ltd', instrument_token: 784129, exchange: 'NSE' },
  { tradingsymbol: 'M&M', name: 'Mahindra & Mahindra Ltd', instrument_token: 519937, exchange: 'NSE' },
  { tradingsymbol: 'INDUSINDBK', name: 'IndusInd Bank Ltd', instrument_token: 1346049, exchange: 'NSE' },
  { tradingsymbol: 'GAIL', name: 'GAIL (India) Ltd', instrument_token: 1207553, exchange: 'NSE' },
  { tradingsymbol: 'BRITANNIA', name: 'Britannia Industries Ltd', instrument_token: 140033, exchange: 'NSE' },
  { tradingsymbol: 'DABUR', name: 'Dabur India Ltd', instrument_token: 197633, exchange: 'NSE' },
  { tradingsymbol: 'IOC', name: 'Indian Oil Corporation', instrument_token: 415745, exchange: 'NSE' },
  { tradingsymbol: 'SHREECEM', name: 'Shree Cement Ltd', instrument_token: 794369, exchange: 'NSE' },
  { tradingsymbol: 'AMBUJACEM', name: 'Ambuja Cements Ltd', instrument_token: 325121, exchange: 'NSE' },
  { tradingsymbol: 'AUROPHARMA', name: 'Aurobindo Pharma Ltd', instrument_token: 70401, exchange: 'NSE' },
  { tradingsymbol: 'TATAPOWER', name: 'Tata Power Company Ltd', instrument_token: 877057, exchange: 'NSE' },
];

// Quick lookup map
const COMMON_TOKENS = {};
COMMON_STOCKS.forEach(s => { COMMON_TOKENS[s.tradingsymbol] = s.instrument_token; });

/**
 * Load and cache the full NSE instrument list
 */
export async function loadInstruments(exchange = 'NSE') {
  if (instrumentCache && Date.now() - cacheTimestamp < CACHE_TTL) {
    return instrumentCache;
  }
  // Try localStorage first
  try {
    const cached = localStorage.getItem('nq_instruments');
    if (cached) {
      const { ts, data } = JSON.parse(cached);
      if (Date.now() - ts < CACHE_TTL) {
        instrumentCache = data;
        cacheTimestamp = ts;
        return data;
      }
    }
  } catch {}

  try {
    const data = await kiteInstruments(exchange);
    instrumentCache = data;
    cacheTimestamp = Date.now();
    // Cache in localStorage (instruments list can be large, store only equity segment)
    const equity = data.filter(i => i.segment === 'NSE' && i.instrument_type === 'EQ');
    localStorage.setItem('nq_instruments', JSON.stringify({ ts: cacheTimestamp, data: equity }));
    return equity;
  } catch (err) {
    console.error('Failed to load instruments:', err);
    return [];
  }
}

/**
 * Search instruments by query (symbol or company name)
 * Falls back to built-in COMMON_STOCKS list if Kite API is unavailable.
 */
export async function searchStocks(query, limit = 10) {
  if (!query || query.length < 1) return [];
  const q = query.toUpperCase();

  // Try Kite instruments first, fallback to common stocks
  let instruments = await loadInstruments();
  if (!instruments || instruments.length === 0) {
    instruments = COMMON_STOCKS;
  }

  return instruments
    .filter(i =>
      i.tradingsymbol?.toUpperCase().includes(q) ||
      i.name?.toUpperCase().includes(q)
    )
    .slice(0, limit)
    .map(i => ({
      symbol: i.tradingsymbol,
      name: i.name,
      token: i.instrument_token,
      exchange: i.exchange || 'NSE',
      segment: i.segment,
    }));
}

/**
 * Get instrument token for a symbol
 */
export async function getInstrumentToken(symbol) {
  // Check common tokens first (instant)
  if (COMMON_TOKENS[symbol]) return COMMON_TOKENS[symbol];

  const instruments = await loadInstruments();
  const match = instruments.find(i => i.tradingsymbol === symbol);
  return match?.instrument_token || null;
}

/**
 * Get instrument info for a symbol
 */
export async function getInstrumentInfo(symbol) {
  const instruments = await loadInstruments();
  const match = instruments.find(i => i.tradingsymbol === symbol);
  if (match) return match;
  // Fallback to common stocks
  return COMMON_STOCKS.find(s => s.tradingsymbol === symbol) || null;
}

// ─── Technical Indicator Calculations ───
// All computed from Kite historical candle data

/**
 * Compute RSI (Relative Strength Index) — 14 period default
 */
export function computeRSI(closes, period = 14) {
  if (closes.length < period + 1) return null;
  let avgGain = 0, avgLoss = 0;

  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) avgGain += diff; else avgLoss -= diff;
  }
  avgGain /= period;
  avgLoss /= period;

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    avgGain = (avgGain * (period - 1) + (diff > 0 ? diff : 0)) / period;
    avgLoss = (avgLoss * (period - 1) + (diff < 0 ? -diff : 0)) / period;
  }
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

/**
 * Compute EMA (Exponential Moving Average)
 */
function ema(data, period) {
  const k = 2 / (period + 1);
  const result = [data[0]];
  for (let i = 1; i < data.length; i++) {
    result.push(data[i] * k + result[i - 1] * (1 - k));
  }
  return result;
}

/**
 * Compute MACD (12, 26, 9)
 */
export function computeMACD(closes) {
  if (closes.length < 26) return null;
  const ema12 = ema(closes, 12);
  const ema26 = ema(closes, 26);
  const macdLine = ema12.map((v, i) => v - ema26[i]);
  const signalLine = ema(macdLine.slice(26), 9);
  const latest = macdLine.length - 1;
  const sigLatest = signalLine.length - 1;
  return {
    macd: macdLine[latest],
    signal: signalLine[sigLatest],
    histogram: macdLine[latest] - signalLine[sigLatest],
  };
}

/**
 * Compute Simple Moving Average
 */
export function computeSMA(closes, period) {
  if (closes.length < period) return null;
  const slice = closes.slice(-period);
  return slice.reduce((a, b) => a + b, 0) / period;
}

/**
 * Compute Bollinger Bands (20 period, 2 std dev)
 */
export function computeBollingerBands(closes, period = 20, mult = 2) {
  const sma = computeSMA(closes, period);
  if (!sma) return null;
  const slice = closes.slice(-period);
  const variance = slice.reduce((sum, v) => sum + (v - sma) ** 2, 0) / period;
  const stdDev = Math.sqrt(variance);
  return { upper: sma + mult * stdDev, middle: sma, lower: sma - mult * stdDev };
}

/**
 * Compute ADX (Average Directional Index) — 14 period
 */
export function computeADX(highs, lows, closes, period = 14) {
  if (highs.length < period * 2) return null;
  const trueRanges = [];
  const plusDM = [];
  const minusDM = [];

  for (let i = 1; i < highs.length; i++) {
    const tr = Math.max(
      highs[i] - lows[i],
      Math.abs(highs[i] - closes[i - 1]),
      Math.abs(lows[i] - closes[i - 1])
    );
    trueRanges.push(tr);
    const upMove = highs[i] - highs[i - 1];
    const downMove = lows[i - 1] - lows[i];
    plusDM.push(upMove > downMove && upMove > 0 ? upMove : 0);
    minusDM.push(downMove > upMove && downMove > 0 ? downMove : 0);
  }

  const smoothed = (arr) => {
    const result = [arr.slice(0, period).reduce((a, b) => a + b, 0)];
    for (let i = period; i < arr.length; i++) {
      result.push(result[result.length - 1] - result[result.length - 1] / period + arr[i]);
    }
    return result;
  };

  const atr = smoothed(trueRanges);
  const sPlusDM = smoothed(plusDM);
  const sMinusDM = smoothed(minusDM);

  const dx = [];
  for (let i = 0; i < atr.length; i++) {
    const plusDI = (sPlusDM[i] / atr[i]) * 100;
    const minusDI = (sMinusDM[i] / atr[i]) * 100;
    const sum = plusDI + minusDI;
    dx.push(sum === 0 ? 0 : (Math.abs(plusDI - minusDI) / sum) * 100);
  }

  if (dx.length < period) return null;
  let adx = dx.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (let i = period; i < dx.length; i++) {
    adx = (adx * (period - 1) + dx[i]) / period;
  }
  return adx;
}

/**
 * Compute all technical indicators from OHLCV candle data
 * @param {Array} candles - Array of [date, open, high, low, close, volume]
 */
export function computeAllIndicators(candles) {
  if (!candles || candles.length < 30) return null;

  const closes = candles.map(c => c[4]);
  const highs = candles.map(c => c[2]);
  const lows = candles.map(c => c[3]);
  const volumes = candles.map(c => c[5]).filter(v => v != null);

  const sma20 = computeSMA(closes, 20);
  const sma50 = computeSMA(closes, 50);
  const sma200 = computeSMA(closes, 200);
  const prevClose = closes.length >= 2 ? closes[closes.length - 2] : null;
  const currentClose = closes[closes.length - 1];

  // EMA 21 / 50 — last value of the EMA series (null if too few bars).
  const ema21Series = closes.length >= 21 ? ema(closes, 21) : null;
  const ema50Series = closes.length >= 50 ? ema(closes, 50) : null;
  const ema_21 = ema21Series ? ema21Series[ema21Series.length - 1] : null;
  const ema_50 = ema50Series ? ema50Series[ema50Series.length - 1] : null;

  // ATR(14) — simple mean of the last 14 true ranges.
  let atr = null;
  if (closes.length >= 15) {
    const trs = [];
    for (let i = 1; i < closes.length; i++) {
      trs.push(Math.max(
        highs[i] - lows[i],
        Math.abs(highs[i] - closes[i - 1]),
        Math.abs(lows[i] - closes[i - 1]),
      ));
    }
    const last14 = trs.slice(-14);
    atr = last14.reduce((a, b) => a + b, 0) / last14.length;
  }

  // 20-bar average volume.
  const volume_avg = volumes.length
    ? volumes.slice(-20).reduce((a, b) => a + b, 0) / Math.min(20, volumes.length)
    : null;

  const rsi = computeRSI(closes);
  const adx = computeADX(highs, lows, closes);

  return {
    rsi,
    macd: computeMACD(closes),
    sma20,
    sma50,
    sma200,
    sma20Trend: sma20 && prevClose ? (currentClose > sma20 ? 'up' : 'down') : null,
    sma50Trend: sma50 && prevClose ? (currentClose > sma50 ? 'up' : 'down') : null,
    sma200Trend: sma200 && prevClose ? (currentClose > sma200 ? 'up' : 'down') : null,
    bollingerBands: computeBollingerBands(closes),
    adx,
    // Aliases + extra fields the StockDetail "Technicals" card reads by name.
    rsi_14: rsi,
    adx_14: adx,
    ema_21,
    ema_50,
    atr,
    volume_avg,
  };
}

/**
 * Fetch historical candles and compute everything for a stock
 * @param {number} token - Instrument token
 * @param {string} interval - 'day', 'minute', '5minute', etc.
 * @param {number} days - Number of days of history
 */
export async function fetchStockData(token, interval = 'day', days = 365) {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - days);

  const fmt = (d) => d.toISOString().split('T')[0];

  try {
    const candles = await kiteHistorical(token, interval, fmt(from), fmt(to));
    if (!candles || !candles.length) return { candles: [], indicators: null };
    return {
      candles,
      indicators: interval === 'day' ? computeAllIndicators(candles) : null,
    };
  } catch (err) {
    console.error('Failed to fetch stock data:', err);
    return { candles: [], indicators: null };
  }
}

/**
 * Get current price data for a stock
 */
export async function fetchCurrentPrice(token) {
  try {
    const data = await kiteLTP([token]);
    return data[token] || data[String(token)] || null;
  } catch (err) {
    console.error('Failed to fetch LTP:', err);
    return null;
  }
}
