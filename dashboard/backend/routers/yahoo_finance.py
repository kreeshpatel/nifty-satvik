"""
Yahoo Finance Router — Fundamentals, news, and supplementary stock data.
Data that Kite doesn't provide (P/E, market cap, dividend, news, peers, shareholding).
Indian stocks use .NS suffix on Yahoo Finance (e.g., RELIANCE.NS).
"""

from fastapi import APIRouter, HTTPException
from functools import lru_cache
import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("niftyquant.yahoo")

# NOTE: unauthenticated access is already blocked by the global auth_middleware
# (main.py) for all /api/yahoo/* EXCEPT /api/yahoo/index-sparklines, which is in
# PUBLIC_PATHS for the public landing page. A router-level auth dependency would
# wrongly gate that public endpoint too. The remaining narrow gap (a deactivated
# user with a still-valid ≤4h token reaching fundamentals) is a tracked P2:
# requires per-endpoint Depends(get_current_user) on the non-public routes.
router = APIRouter(prefix="/yahoo", tags=["yahoo-finance"])

# Cache with TTL — store (timestamp, data)
_cache = {}
CACHE_TTL = 300  # 5 minutes

# Valid intervals and periods for Yahoo Finance
VALID_YF_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
VALID_YF_PERIODS = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}


def _get_cached(key):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _set_cached(key, data):
    _cache[key] = (time.time(), data)


def _yf_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert trading symbol to Yahoo Finance format."""
    symbol = symbol.upper().replace(" ", "")
    if exchange == "BSE":
        return f"{symbol}.BO"
    return f"{symbol}.NS"


# ── Daily-close quotes (2026-11-02, hosting cost) ─────────────────────────
# The product is a weekend-scanned weekly-swing book; nothing needs an
# intraday price. Quote endpoints therefore serve the last COMPLETED NSE
# daily bar from Yahoo, and the cache holds it until the next 16:00 IST
# settle — so Yahoo is called at most once per symbol per trading day, and
# the frontend no longer polls (which let the Fly machine suspend).
_IST = timezone(timedelta(hours=5, minutes=30))
_CLOSE_SETTLE_HOUR_IST = 16  # NSE closes 15:30; give Yahoo 30 min to settle


def _last_close_boundary(now: datetime | None = None) -> datetime:
    """Most recent weekday 16:00 IST at or before `now`.

    NSE holidays are not modelled: on a holiday the cache refreshes once and
    gets the same last bar back, which is harmless.
    """
    now = (now or datetime.now(_IST)).astimezone(_IST)
    boundary = now.replace(hour=_CLOSE_SETTLE_HOUR_IST, minute=0, second=0, microsecond=0)
    if now < boundary:
        boundary -= timedelta(days=1)
    while boundary.weekday() >= 5:  # Sat/Sun → back to Friday
        boundary -= timedelta(days=1)
    return boundary


def _fresh_since_close(cached_at: float, now: datetime | None = None) -> bool:
    """True when a cache entry was written after the latest daily-close boundary."""
    return cached_at >= _last_close_boundary(now).timestamp()


def _quote_from_daily_bars(bars, boundary_date) -> dict | None:
    """Build a quote from a daily OHLCV frame, using only completed bars.

    Bars dated after `boundary_date` (today's still-forming bar, before the
    16:00 IST settle) are dropped, so an intraday price can never leak in.
    """
    if bars is None or len(bars) == 0 or "Close" not in bars:
        return None
    bars = bars.dropna(subset=["Close"])
    bars = bars[[d.date() <= boundary_date for d in bars.index]]
    if len(bars) == 0:
        return None
    last = bars.iloc[-1]
    prev_close = float(bars["Close"].iloc[-2]) if len(bars) >= 2 else None
    close = float(last["Close"])
    change = round(close - prev_close, 2) if prev_close else None
    change_pct = round((close - prev_close) / prev_close * 100, 2) if prev_close else None

    def _num(col):
        v = last.get(col) if hasattr(last, "get") else None
        try:
            return None if v is None or v != v else float(v)  # v != v → NaN
        except (TypeError, ValueError):
            return None

    return {
        "last_price": round(close, 2),
        "previous_close": round(prev_close, 2) if prev_close else None,
        "open": _num("Open"),
        "high": _num("High"),
        "low": _num("Low"),
        "volume": _num("Volume"),
        "change": change,
        "change_pct": change_pct,
        "as_of": bars.index[-1].date().isoformat(),
    }


def _daily_close_quotes(yf_syms: list[str], now: datetime | None = None) -> dict:
    """{yf_symbol: quote} from ONE batched Yahoo daily-bar download. Blocking."""
    import pandas as pd
    import yfinance as yf

    if not yf_syms:
        return {}
    boundary_date = _last_close_boundary(now).date()
    df = yf.download(
        yf_syms, period="10d", interval="1d", group_by="ticker",
        auto_adjust=False, progress=False, threads=True,
    )
    out = {}
    for ys in yf_syms:
        try:
            if isinstance(df.columns, pd.MultiIndex):
                if ys not in df.columns.get_level_values(0):
                    continue
                bars = df[ys]
            else:
                bars = df
            quote = _quote_from_daily_bars(bars, boundary_date)
            if quote:
                out[ys] = quote
        except Exception as e:  # one bad ticker must not sink the batch
            logger.warning(f"Daily-close quote skip {ys}: {e}")
    return out


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str, exchange: str = "NSE"):
    """
    Get stock fundamentals from Yahoo Finance.
    Returns: market cap, P/E, P/B, dividend yield, 52W high/low, sector, industry, etc.
    """
    cache_key = f"fundamentals:{symbol}:{exchange}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        yf_sym = _yf_symbol(symbol, exchange)
        ticker = yf.Ticker(yf_sym)
        info = ticker.info or {}

        result = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "exchange": exchange,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "enterprise_value": info.get("enterpriseValue"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "price_to_book": info.get("priceToBook"),  # key the StockDetail UI reads
            "peg_ratio": info.get("trailingPegRatio") or info.get("pegRatio"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "book_value": info.get("bookValue"),
            "face_value": info.get("faceValue"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),  # key the StockDetail UI reads
            "debt_to_equity": info.get("debtToEquity"),
            "revenue": info.get("totalRevenue"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_day_avg": info.get("fiftyDayAverage"),
            "two_hundred_day_avg": info.get("twoHundredDayAverage"),
            "avg_volume": info.get("averageVolume"),
            "avg_volume_10d": info.get("averageDailyVolume10Day"),
            "shares_outstanding": info.get("sharesOutstanding"),
            "float_shares": info.get("floatShares"),
            "held_percent_insiders": info.get("heldPercentInsiders"),
            "held_percent_institutions": info.get("heldPercentInstitutions"),
            "beta": info.get("beta"),
            "currency": info.get("currency", "INR"),
        }

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Yahoo fundamentals error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch fundamentals")


@router.get("/news/{symbol}")
async def get_news(symbol: str, exchange: str = "NSE"):
    """
    Get recent news for a stock from Yahoo Finance.
    """
    cache_key = f"news:{symbol}:{exchange}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        yf_sym = _yf_symbol(symbol, exchange)
        ticker = yf.Ticker(yf_sym)
        raw_news = ticker.news or []

        # yfinance >= 0.2.31 returns news in a different format
        # Handle both old format (list of dicts) and new format (list or dict with 'title'/'content')
        result = []
        items = raw_news if isinstance(raw_news, list) else []

        for item in items[:10]:
            # New yfinance format may nest content under different keys
            title = (
                item.get("title")
                or item.get("content", {}).get("title")
                or item.get("headline")
                or ""
            )
            publisher = (
                item.get("publisher")
                or item.get("content", {}).get("provider", {}).get("displayName")
                or item.get("source")
                or ""
            )
            link = (
                item.get("link")
                or item.get("content", {}).get("clickThroughUrl", {}).get("url")
                or item.get("url")
                or ""
            )
            published = (
                item.get("providerPublishTime")
                or item.get("content", {}).get("pubDate")
                or item.get("published")
            )
            # Convert string dates to timestamps if needed
            if isinstance(published, str):
                try:
                    from datetime import datetime
                    published = int(datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp())
                except Exception:
                    published = None

            if title:  # Only include items with actual titles
                result.append({
                    "title": title,
                    "publisher": publisher or "Yahoo Finance",
                    "link": link,
                    "published": published,
                    "type": item.get("type", "STORY"),
                })

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Yahoo news error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch news")


@router.get("/peers/{symbol}")
async def get_peers(symbol: str, exchange: str = "NSE"):
    """
    Get peer comparison data — same-sector stocks with key metrics.
    """
    cache_key = f"peers:{symbol}:{exchange}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf

        # Sector mapping for Indian stocks
        SECTOR_PEERS = {
            "Energy": ["RELIANCE", "ONGC", "BPCL", "IOC", "GAIL"],
            "Financial Services": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"],
            "Information Technology": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
            "Automobile": ["TATAMOTORS", "MARUTI", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"],
            "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA"],
            "Metals": ["TATASTEEL", "HINDALCO", "JSWSTEEL", "VEDL", "COALINDIA"],
            "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR"],
            "Construction": ["LT", "ULTRACEMCO", "GRASIM", "SHREECEM", "AMBUJACEM"],
        }

        # Get the stock's sector first
        yf_sym = _yf_symbol(symbol, exchange)
        ticker = yf.Ticker(yf_sym)
        info = ticker.info or {}
        sector = info.get("sector", "")

        # Find peer list
        peers = None
        for sec_name, sec_peers in SECTOR_PEERS.items():
            if symbol.upper() in sec_peers:
                peers = sec_peers
                break

        if not peers:
            # Fallback: use NIFTY 50 heavyweights
            peers = ["RELIANCE", "HDFCBANK", "INFY", "TCS", "ICICIBANK"]

        # Make sure target symbol is in the list
        if symbol.upper() not in peers:
            peers = [symbol.upper()] + peers[:4]

        result = []
        for peer_sym in peers[:5]:
            try:
                p = yf.Ticker(_yf_symbol(peer_sym, exchange))
                p_info = p.info or {}
                result.append({
                    "symbol": peer_sym,
                    "name": p_info.get("shortName", peer_sym),
                    "ltp": p_info.get("currentPrice") or p_info.get("regularMarketPrice"),
                    "change_pct": p_info.get("regularMarketChangePercent"),
                    "market_cap": p_info.get("marketCap"),
                    "pe_ratio": p_info.get("trailingPE"),
                    "pb_ratio": p_info.get("priceToBook"),
                    "dividend_yield": p_info.get("dividendYield"),
                    "is_target": peer_sym.upper() == symbol.upper(),
                })
            except Exception:
                continue

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Yahoo peers error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch peers")


@router.get("/shareholding/{symbol}")
async def get_shareholding(symbol: str, exchange: str = "NSE"):
    """
    Get major holders / institutional ownership from Yahoo Finance.
    """
    cache_key = f"shareholding:{symbol}:{exchange}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        yf_sym = _yf_symbol(symbol, exchange)
        ticker = yf.Ticker(yf_sym)
        info = ticker.info or {}

        result = {
            "symbol": symbol,
            "promoters": info.get("heldPercentInsiders"),
            "fii": info.get("heldPercentInstitutions"),
            "public": None,  # Calculated below
        }

        # Calculate public holding
        promoters = result["promoters"] or 0
        fii = result["fii"] or 0
        result["public"] = max(0, 1 - promoters - fii) if (promoters or fii) else None

        # Try to get major holders dataframe
        try:
            holders = ticker.major_holders
            if holders is not None and not holders.empty:
                result["major_holders"] = holders.to_dict("records")
        except Exception:
            pass

        # Try institutional holders
        try:
            inst = ticker.institutional_holders
            if inst is not None and not inst.empty:
                result["top_institutions"] = inst.head(5).to_dict("records")
        except Exception:
            pass

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Yahoo shareholding error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch shareholding")


@router.get("/historical/{symbol}")
async def get_historical(symbol: str, interval: str = "1d", period: str = "1y", exchange: str = "NSE"):
    """
    Get historical OHLCV candle data from Yahoo Finance.
    No Kite auth needed. Works for any NSE/BSE stock.
    interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo
    period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
    """
    if interval not in VALID_YF_INTERVALS:
        raise HTTPException(status_code=400, detail=f"Invalid interval. Must be one of: {', '.join(sorted(VALID_YF_INTERVALS))}")
    if period not in VALID_YF_PERIODS:
        raise HTTPException(status_code=400, detail=f"Invalid period. Must be one of: {', '.join(sorted(VALID_YF_PERIODS))}")

    cache_key = f"hist:{symbol}:{interval}:{period}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        yf_sym = _yf_symbol(symbol, exchange)
        ticker = yf.Ticker(yf_sym)
        hist = ticker.history(period=period, interval=interval)

        if hist is None or hist.empty:
            return []

        candles = []
        hist = hist.reset_index()
        date_col = "Datetime" if "Datetime" in hist.columns else "Date"

        for _, row in hist.iterrows():
            candles.append([
                str(row[date_col]),
                round(float(row["Open"]), 2),
                round(float(row["High"]), 2),
                round(float(row["Low"]), 2),
                round(float(row["Close"]), 2),
                int(row["Volume"]) if row["Volume"] else 0,
            ])

        _set_cached(cache_key, candles)
        return candles

    except Exception as e:
        logger.error(f"Yahoo historical error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch historical data")


@router.get("/quote/{symbol}")
async def get_quote(symbol: str, exchange: str = "NSE"):
    """
    Quote for one symbol: price fields are the last COMPLETED daily close
    (see _quote_from_daily_bars); name / 52W range / market cap / P/E come
    from Yahoo's info. Cached until the next 16:00 IST close boundary.
    """
    cache_key = f"quote:{symbol}:{exchange}"
    entry = _cache.get(cache_key)
    if entry and _fresh_since_close(entry[0]):
        return entry[1]

    try:
        import yfinance as yf
        yf_sym = _yf_symbol(symbol, exchange)

        def _fetch():
            info = yf.Ticker(yf_sym).info or {}
            daily = _daily_close_quotes([yf_sym]).get(yf_sym) or {}
            return info, daily

        info, daily = await asyncio.to_thread(_fetch)
        if not daily:
            raise ValueError("no completed daily bar")

        result = {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "last_price": daily["last_price"],
            "previous_close": daily["previous_close"],
            "open": daily["open"],
            "high": daily["high"],
            "low": daily["low"],
            "close": daily["last_price"],
            "volume": daily["volume"],
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "change": daily["change"],
            "change_pct": daily["change_pct"],
            "as_of": daily["as_of"],
        }
        _cache[cache_key] = (time.time(), result)
        return result

    except Exception as e:
        logger.error(f"Yahoo quote error for {symbol}: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch quote")


@router.get("/quote-batch")
async def get_quote_batch(symbols: str, exchange: str = "NSE"):
    """
    Daily-close prices for multiple symbols in one request.
    Returns: { "IDBI": {last_price, previous_close, change, change_pct, as_of, ...}, ... }

    `last_price` is the last COMPLETED NSE daily close, not a live price.
    Missing symbols are fetched in ONE batched Yahoo download (off the event
    loop) and cached until the next 16:00 IST close boundary.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {}
    # Guard against abuse
    symbol_list = symbol_list[:50]

    result = {}
    missing = []

    for sym in symbol_list:
        entry = _cache.get(f"quote-batch:{sym}:{exchange}")
        if entry and _fresh_since_close(entry[0]):
            result[sym] = entry[1]
        else:
            missing.append(sym)

    if missing:
        try:
            yf_syms = [_yf_symbol(s, exchange) for s in missing]
            fetched = await asyncio.to_thread(_daily_close_quotes, yf_syms)
            now = time.time()
            for sym, yf_sym in zip(missing, yf_syms):
                quote = fetched.get(yf_sym)
                if quote is None:
                    continue
                result[sym] = quote
                _cache[f"quote-batch:{sym}:{exchange}"] = (now, quote)
        except Exception as e:
            logger.error(f"Batch quote error: {e}")
            # Partial response is still useful; don't raise

    return result


# Yahoo Finance tickers for Indian indices
YAHOO_INDEX_MAP = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "FIN NIFTY": "NIFTY_FIN_SERVICE.NS",
    "SENSEX": "^BSESN",
    "INDIA VIX": "^INDIAVIX",
    "USD/INR": "USDINR=X",
}


@router.get("/index-sparklines")
async def get_index_sparklines():
    """
    Get intraday sparkline data for major indices.
    Returns 30min candle close prices for the latest trading session.
    Change% is calculated from previous day's close (not today's open).
    No Kite auth needed — uses Yahoo Finance.
    """
    cache_key = "index-sparklines"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf

        # Each index needs 2 blocking Yahoo calls (daily history + intraday
        # 5m candles). Running all 6 indices x 2 calls sequentially in a
        # for-loop inside an `async def` endpoint meant every 5-minute cache
        # miss stalled for up to 12 sequential round trips AND blocked the
        # event loop — every other request on the backend queued behind it.
        # Fetch all 6 indices concurrently in worker threads instead.
        def _fetch_index(name: str, yf_sym: str) -> dict | None:
            try:
                ticker = yf.Ticker(yf_sym)

                # 1. Get daily data for accurate previous close
                daily = ticker.history(period="5d", interval="1d")
                prev_close = None
                daily_ltp = None
                daily_change_pct = 0

                if daily is not None and len(daily) >= 2:
                    # Previous trading day's close
                    prev_close = round(float(daily["Close"].iloc[-2]), 2)
                    # Today's / latest close
                    daily_ltp = round(float(daily["Close"].iloc[-1]), 2)
                    if prev_close:
                        daily_change_pct = round(((daily_ltp - prev_close) / prev_close) * 100, 2)
                elif daily is not None and len(daily) == 1:
                    daily_ltp = round(float(daily["Close"].iloc[-1]), 2)

                # 2. Get 5min candles for today's intraday trend (~75 points per session)
                hist = ticker.history(period="2d", interval="5m")
                sparkline = None

                if hist is not None and not hist.empty:
                    hist = hist.reset_index()
                    date_col = "Datetime" if "Datetime" in hist.columns else "Date"
                    hist["_date"] = hist[date_col].dt.date
                    dates = sorted(hist["_date"].unique())

                    # Use the latest trading day with enough data
                    for d in reversed(dates):
                        day_data = hist[hist["_date"] == d]
                        closes = day_data["Close"].dropna().tolist()
                        if len(closes) >= 10:
                            sparkline = [round(c, 2) for c in closes]
                            break

                if sparkline or daily_ltp:
                    return {
                        "sparkline": sparkline or [],
                        "ltp": daily_ltp or (sparkline[-1] if sparkline else None),
                        "prev_close": prev_close,
                        "change_pct": daily_change_pct,
                    }
                return None
            except Exception as e:
                logger.debug(f"Sparkline error for {name}: {e}")
                return None

        names = list(YAHOO_INDEX_MAP.keys())
        fetched = await asyncio.gather(
            *(asyncio.to_thread(_fetch_index, name, yf_sym) for name, yf_sym in YAHOO_INDEX_MAP.items())
        )
        result = {name: data for name, data in zip(names, fetched) if data is not None}

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"Yahoo index sparklines error: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch sparklines")
