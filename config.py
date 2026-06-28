"""nifty-satvik — project configuration (long-horizon only).

Carries the universe (``NIFTY_500``), the NSE holiday calendar (``NSE_HOLIDAYS``),
and the sector map (``SECTOR_MAP``) verbatim from the validated source, plus the
long-horizon cost model and the universe-eligibility thresholds. Lean by design:
none of the retired v1 / regime-tier / dashboard constants are carried.

Single source of truth for: the tradeable universe, the both-legs delivery cost
model, the liquidity-tier slippage, and the large+mid / solvency thresholds.
"""
from __future__ import annotations

from pathlib import Path

# ── Directories ───────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
MODELS_DIR = BASE_DIR / "models"
ALL_DIRS = [DATA_DIR, RESULTS_DIR, MODELS_DIR]


def ensure_dirs() -> None:
    """Create the project data/results/models directories if absent."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# ── Cost model — delivery equity, charged on BOTH legs ────
# brokerage 0.03%/leg + STT 0.10%/leg (delivery STT is per-leg, buy AND sell).
BROKERAGE_PCT = 0.0003
STT_PCT = 0.001


def delivery_leg_cost(notional: float) -> float:
    """Brokerage + STT for ONE delivery-equity leg (buy OR sell). The backtest /
    live paths add tiered slippage + market impact on top of this base."""
    return float(notional) * (BROKERAGE_PCT + STT_PCT)


# Tiered slippage by liquidity tier (point-in-time 20d rupee ADV), per leg, plus
# an Almgren square-root temporary-impact term applied above ~0.5% ADV:
#   impact_pct = IMPACT_ETA * sigma_daily * sqrt(position_value / adv_rupees)
SLIPPAGE = {"LARGE_CAP": 0.0005, "MID_CAP": 0.0022, "SMALL_CAP": 0.0040}
IMPACT_ETA = 1.0

# ── Universe eligibility thresholds ───────────────────────
ADV_LARGE_CAP_RS = 50e7    # >= Rs 50 cr/day 20d rupee ADV  -> LARGE_CAP tier
ADV_MID_CAP_RS = 5e7       # >= Rs 5 cr/day                 -> MID_CAP (the large+mid floor)
MAX_ADV_PARTICIPATION = 0.05      # position cap = 5% of the name's 20d rupee ADV
ADV_PERSISTENCE_WINDOW = 252      # trailing rolling-median ADV window (spike-robust large+mid mask)
DE_MAX = 1.5               # solvency keep-rule: 0 <= D/E < DE_MAX

# Deposit-taking / balance-sheet-lending financials, for which the Screener PIT
# store reports D/E = NaN (debt-to-equity is ill-defined for banks & NBFCs whose
# liabilities ARE their business). Used by the solvency mask's financial branch.
FINANCIAL_SECTORS = frozenset({"Banking", "Finance_NBFC"})


# ── Nifty-500 universe (official NSE list snapshot 2025-07-20; 500 names) ──
NIFTY_500 = [
    '360ONE', '3MINDIA', 'AADHARHFC', 'AARTIIND', 'AAVAS', 'ABB',
    'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ABREL', 'ABSLAMC', 'ACC',
    'ACE', 'ACMESOLAR', 'ADANIENSOL', 'ADANIENT', 'ADANIGREEN', 'ADANIPORTS',
    'ADANIPOWER', 'AEGISLOG', 'AFCONS', 'AFFLE', 'AIAENG', 'AIIL',
    'AJANTPHARM', 'AKUMS', 'ALIVUS', 'ALKEM', 'ALKYLAMINE', 'ALOKINDS',
    'AMBER', 'AMBUJACEM', 'ANANDRATHI', 'ANANTRAJ', 'ANGELONE', 'APARINDS',
    'APLAPOLLO', 'APLLTD', 'APOLLOHOSP', 'APOLLOTYRE', 'APTUS', 'ARE&M',
    'ASAHIINDIA', 'ASHOKLEY', 'ASIANPAINT', 'ASTERDM', 'ASTRAL', 'ASTRAZEN',
    'ATGL', 'ATUL', 'AUBANK', 'AUROPHARMA', 'AWL', 'AXISBANK',
    'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJAJHFL', 'BAJAJHLDNG', 'BAJFINANCE', 'BALKRISIND',
    'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BANKINDIA', 'BASF', 'BATAINDIA',
    'BAYERCROP', 'BBTC', 'BDL', 'BEL', 'BEML', 'BERGEPAINT',
    'BHARATFORG', 'BHARTIARTL', 'BHARTIHEXA', 'BHEL', 'BIKAJI', 'BIOCON',
    'BLS', 'BLUEDART', 'BLUESTARCO', 'BOSCHLTD', 'BPCL', 'BRIGADE',
    'BRITANNIA', 'BSE', 'BSOFT', 'CAMPUS', 'CAMS', 'CANBK',
    'CANFINHOME', 'CAPLIPOINT', 'CARBORUNIV', 'CASTROLIND', 'CCL', 'CDSL',
    'CEATLTD', 'CENTRALBK', 'CENTURYPLY', 'CERA', 'CESC', 'CGCL',
    'CGPOWER', 'CHALET', 'CHAMBLFERT', 'CHENNPETRO', 'CHOLAFIN', 'CHOLAHLDNG',
    'CIPLA', 'CLEAN', 'COALINDIA', 'COCHINSHIP', 'COFORGE', 'COHANCE',
    'COLPAL', 'CONCOR', 'CONCORDBIO', 'COROMANDEL', 'CRAFTSMAN', 'CREDITACC',
    'CRISIL', 'CROMPTON', 'CUB', 'CUMMINSIND', 'CYIENT', 'DABUR',
    'DALBHARAT', 'DATAPATTNS', 'DBREALTY', 'DCMSHRIRAM', 'DEEPAKFERT', 'DEEPAKNTR',
    'DELHIVERY', 'DEVYANI', 'DIVISLAB', 'DIXON', 'DLF', 'DMART',
    'DOMS', 'DRREDDY', 'ECLERX', 'EICHERMOT', 'EIDPARRY', 'EIHOTEL',
    'ELECON', 'ELGIEQUIP', 'EMAMILTD', 'EMCURE', 'ENDURANCE', 'ENGINERSIN',
    'ERIS', 'ESCORTS', 'ETERNAL', 'EXIDEIND', 'FACT', 'FEDERALBNK',
    'FINCABLES', 'FINPIPE', 'FIRSTCRY', 'FIVESTAR', 'FLUOROCHEM', 'FORTIS',
    'FSL', 'GAIL', 'GESHIP', 'GICRE', 'GILLETTE', 'GLAND',
    'GLAXO', 'GLENMARK', 'GMDCLTD', 'GMRAIRPORT', 'GNFC', 'GODFRYPHLP',
    'GODIGIT', 'GODREJAGRO', 'GODREJCP', 'GODREJIND', 'GODREJPROP', 'GPIL',
    'GPPL', 'GRANULES', 'GRAPHITE', 'GRASIM', 'GRAVITA', 'GRSE',
    'GSPL', 'GUJGASLTD', 'GVT&D', 'HAL', 'HAPPSTMNDS', 'HAVELLS',
    'HBLENGINE', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEG',
    'HEROMOTOCO', 'HFCL', 'HINDALCO', 'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR',
    'HINDZINC', 'HOMEFIRST', 'HONASA', 'HONAUT', 'HSCL', 'HUDCO',
    'HYUNDAI', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDBI', 'IDEA',
    'IDFCFIRSTB', 'IEX', 'IFCI', 'IGIL', 'IGL', 'IIFL',
    'IKS', 'INDGN', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIANB',
    'INDIGO', 'INDUSINDBK', 'INDUSTOWER', 'INFY', 'INOXINDIA', 'INOXWIND',
    'INTELLECT', 'IOB', 'IOC', 'IPCALAB', 'IRB', 'IRCON',
    'IRCTC', 'IREDA', 'IRFC', 'ITC', 'ITI', 'J&KBANK',
    'JBCHEPHARM', 'JBMA', 'JINDALSAW', 'JINDALSTEL', 'JIOFIN', 'JKCEMENT',
    'JKTYRE', 'JMFINANCIL', 'JPPOWER', 'JSL', 'JSWENERGY', 'JSWHL',
    'JSWINFRA', 'JSWSTEEL', 'JUBLFOOD', 'JUBLINGREA', 'JUBLPHARMA', 'JUSTDIAL',
    'JWL', 'JYOTHYLAB', 'JYOTICNC', 'KAJARIACER', 'KALYANKJIL', 'KANSAINER',
    'KARURVYSYA', 'KAYNES', 'KEC', 'KEI', 'KFINTECH', 'KIMS',
    'KIRLOSBROS', 'KIRLOSENG', 'KNRCON', 'KOTAKBANK', 'KPIL', 'KPITTECH',
    'KPRMILL', 'LALPATHLAB', 'LATENTVIEW', 'LAURUSLABS', 'LEMONTREE', 'LICHSGFIN',
    'LICI', 'LINDEINDIA', 'LLOYDSME', 'LODHA', 'LT', 'LTF',
    'LTFOODS', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN',
    'MAHABANK', 'MAHSEAMLES', 'MANAPPURAM', 'MANKIND', 'MANYAVAR', 'MAPMYINDIA',
    'MARICO', 'MARUTI', 'MASTEK', 'MAXHEALTH', 'MAZDOCK', 'MCX',
    'MEDANTA', 'METROPOLIS', 'MFSL', 'MGL', 'MINDACORP', 'MMTC',
    'MOTHERSON', 'MOTILALOFS', 'MPHASIS', 'MRF', 'MRPL', 'MSUMI',
    'MUTHOOTFIN', 'NAM-INDIA', 'NATCOPHARM', 'NATIONALUM', 'NAUKRI', 'NAVA',
    'NAVINFLUOR', 'NBCC', 'NCC', 'NESTLEIND', 'NETWEB', 'NETWORK18',
    'NEULANDLAB', 'NEWGEN', 'NH', 'NHPC', 'NIACL', 'NIVABUPA',
    'NLCINDIA', 'NMDC', 'NSLNISP', 'NTPC', 'NTPCGREEN', 'NUVAMA',
    'NYKAA', 'OBEROIRLTY', 'OFSS', 'OIL', 'OLAELEC', 'OLECTRA',
    'ONGC', 'PAGEIND', 'PATANJALI', 'PAYTM', 'PCBL', 'PEL',
    'PERSISTENT', 'PETRONET', 'PFC', 'PFIZER', 'PGEL', 'PHOENIXLTD',
    'PIDILITIND', 'PIIND', 'PNB', 'PNBHOUSING', 'PNCINFRA', 'POLICYBZR',
    'POLYCAB', 'POLYMED', 'POONAWALLA', 'POWERGRID', 'POWERINDIA', 'PPLPHARMA',
    'PRAJIND', 'PREMIERENE', 'PRESTIGE', 'PTCIL', 'PVRINOX', 'RADICO',
    'RAILTEL', 'RAINBOW', 'RAMCOCEM', 'RAYMOND', 'RAYMONDLSL', 'RBLBANK',
    'RCF', 'RECLTD', 'REDINGTON', 'RELIANCE', 'RENUKA', 'RHIM',
    'RITES', 'RKFORGE', 'ROUTE', 'RPOWER', 'RRKABEL', 'RTNINDIA',
    'RVNL', 'SAGILITY', 'SAIL', 'SAILIFE', 'SAMMAANCAP', 'SAPPHIRE',
    'SARDAEN', 'SAREGAMA', 'SBFC', 'SBICARD', 'SBILIFE', 'SBIN',
    'SCHAEFFLER', 'SCHNEIDER', 'SCI', 'SHREECEM', 'SHRIRAMFIN', 'SHYAMMETL',
    'SIEMENS', 'SIGNATURE', 'SJVN', 'SKFINDIA', 'SOBHA', 'SOLARINDS',
    'SONACOMS', 'SONATSOFTW', 'SRF', 'STARHEALTH', 'SUMICHEM', 'SUNDARMFIN',
    'SUNDRMFAST', 'SUNPHARMA', 'SUNTV', 'SUPREMEIND', 'SUZLON', 'SWANENERGY',
    'SWIGGY', 'SWSOLAR', 'SYNGENE', 'SYRMA', 'TANLA', 'TARIL',
    'TATACHEM', 'TATACOMM', 'TATACONSUM', 'TATAELXSI', 'TATAINVEST', 'TATAMOTORS',
    'TATAPOWER', 'TATASTEEL', 'TATATECH', 'TBOTEK', 'TCS', 'TECHM',
    'TECHNOE', 'TEJASNET', 'THERMAX', 'TIINDIA', 'TIMKEN', 'TITAGARH',
    'TITAN', 'TORNTPHARM', 'TORNTPOWER', 'TRENT', 'TRIDENT', 'TRITURBINE',
    'TRIVENI', 'TTML', 'TVSMOTOR', 'UBL', 'UCOBANK', 'ULTRACEMCO',
    'UNIONBANK', 'UNITDSPR', 'UNOMINDA', 'UPL', 'USHAMART', 'UTIAMC',
    'VBL', 'VEDL', 'VGUARD', 'VIJAYA', 'VMM', 'VOLTAS',
    'VTL', 'WAAREEENER', 'WELCORP', 'WELSPUNLIV', 'WESTLIFE', 'WHIRLPOOL',
    'WIPRO', 'WOCKPHARMA', 'YESBANK', 'ZEEL', 'ZENSARTECH', 'ZENTEC',
    'ZFCVINDIA', 'ZYDUSLIFE',
]

# ── NSE holiday calendar (ISO dates) — phantom-bar drop in the OHLCV cleaner ──
NSE_HOLIDAYS = {
    '2025-02-26', '2025-03-14', '2025-03-31', '2025-04-10',
    '2025-04-14', '2025-04-18', '2025-05-01', '2025-06-07',
    '2025-08-15', '2025-08-16', '2025-08-27', '2025-10-02',
    '2025-10-21', '2025-10-22', '2025-11-05', '2025-11-26',
    '2025-12-25', '2026-01-26', '2026-02-17', '2026-03-03',
    '2026-03-20', '2026-03-30', '2026-04-03', '2026-04-14',
    '2026-05-01', '2026-05-28', '2026-06-26', '2026-08-15',
    '2026-08-17', '2026-09-04', '2026-10-02', '2026-10-12',
    '2026-10-26', '2026-11-16', '2026-12-25',
}

# ── Sector map (ticker -> sector label) ──
SECTOR_MAP = {
    'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking', 'AXISBANK': 'Banking',
    'KOTAKBANK': 'Banking', 'BANKBARODA': 'Banking', 'CANBK': 'Banking', 'PNB': 'Banking',
    'FEDERALBNK': 'Banking', 'IDFCFIRSTB': 'Banking', 'INDUSINDBK': 'Banking', 'CUB': 'Banking',
    'AUBANK': 'Banking', 'BANDHANBNK': 'Banking', 'KARURVYSYA': 'Banking', 'INDIANB': 'Banking',
    'IDBI': 'Banking', 'UCOBANK': 'Banking', 'UNIONBANK': 'Banking', 'EQUITASBNK': 'Banking',
    'UJJIVANSFB': 'Banking', 'TCS': 'IT', 'INFY': 'IT', 'HCLTECH': 'IT',
    'WIPRO': 'IT', 'TECHM': 'IT', 'LTIM': 'IT', 'LTTS': 'IT',
    'MPHASIS': 'IT', 'PERSISTENT': 'IT', 'COFORGE': 'IT', 'HAPPSTMNDS': 'IT',
    'OFSS': 'IT', 'NAUKRI': 'IT', 'TATAELXSI': 'IT', 'ECLERX': 'IT',
    'MASTEK': 'IT', 'NEWGEN': 'IT', 'INTELLECT': 'IT', 'TANLA': 'IT',
    'INDIAMART': 'IT', 'AFFLE': 'IT', 'RELIANCE': 'Energy', 'ONGC': 'Energy',
    'BPCL': 'Energy', 'IOC': 'Energy', 'GAIL': 'Energy', 'PETRONET': 'Energy',
    'HINDPETRO': 'Energy', 'ADANIENT': 'Energy', 'ADANIGREEN': 'Energy', 'ADANIPOWER': 'Energy',
    'ADANIENSOL': 'Energy', 'ADANIPORTS': 'Energy', 'TATAPOWER': 'Energy', 'NTPC': 'Energy',
    'POWERGRID': 'Energy', 'PFC': 'Finance_NBFC', 'RECLTD': 'Finance_NBFC', 'COALINDIA': 'Energy',
    'JSWENERGY': 'Energy', 'IGL': 'Energy', 'MGL': 'Energy', 'GUJGASLTD': 'Energy',
    'GSPL': 'Energy', 'MARUTI': 'Auto', 'M&M': 'Auto', 'BAJAJ-AUTO': 'Auto',
    'TATAMOTORS': 'Auto', 'EICHERMOT': 'Auto', 'HEROMOTOCO': 'Auto', 'TVSMOTOR': 'Auto',
    'ESCORTS': 'Auto', 'MOTHERSON': 'Auto', 'BOSCHLTD': 'Auto', 'EXIDEIND': 'Auto',
    'ENDURANCE': 'Auto', 'VARROC': 'Auto', 'CEATLTD': 'Auto', 'MRF': 'Auto',
    'UNOMINDA': 'Auto', 'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG',
    'BRITANNIA': 'FMCG', 'DABUR': 'FMCG', 'MARICO': 'FMCG', 'GODREJCP': 'FMCG',
    'COLPAL': 'FMCG', 'EMAMILTD': 'FMCG', 'TATACONSUM': 'FMCG', 'TATACONSUMER': 'FMCG',
    'VBL': 'FMCG', 'UBL': 'FMCG', 'BIKAJI': 'FMCG', 'BATAINDIA': 'FMCG',
    'PAGEIND': 'FMCG', 'RELAXO': 'FMCG', 'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma',
    'CIPLA': 'Pharma', 'DIVISLAB': 'Pharma', 'LUPIN': 'Pharma', 'BIOCON': 'Pharma',
    'AUROPHARMA': 'Pharma', 'TORNTPHARM': 'Pharma', 'ALKEM': 'Pharma', 'IPCALAB': 'Pharma',
    'LALPATHLAB': 'Pharma', 'LAURUSLABS': 'Pharma', 'AJANTPHARM': 'Pharma', 'NATCOPHARM': 'Pharma',
    'GRANULES': 'Pharma', 'GLENMARK': 'Pharma', 'ABBOTINDIA': 'Pharma', 'GLAXO': 'Pharma',
    'METROPOLIS': 'Pharma', 'FORTIS': 'Pharma', 'MAXHEALTH': 'Pharma', 'KIMS': 'Pharma',
    'APOLLOHOSP': 'Pharma', 'SPARC': 'Pharma', 'SUVENPHAR': 'Pharma', 'ZYDUSLIFE': 'Pharma',
    'BAJFINANCE': 'Finance_NBFC', 'BAJAJFINSV': 'Finance_NBFC', 'CHOLAFIN': 'Finance_NBFC', 'MUTHOOTFIN': 'Finance_NBFC',
    'MANAPPURAM': 'Finance_NBFC', 'LICHSGFIN': 'Finance_NBFC', 'HDFCAMC': 'Finance_NBFC', 'ICICIGI': 'Finance_NBFC',
    'ICICIPRULI': 'Finance_NBFC', 'SBILIFE': 'Finance_NBFC', 'SBICARD': 'Finance_NBFC', 'HDFCLIFE': 'Finance_NBFC',
    'STARHEALTH': 'Finance_NBFC', 'BAJAJHLDNG': 'Finance_NBFC', 'MFSL': 'Finance_NBFC', 'ANGELONE': 'Finance_NBFC',
    'MOTILALOFS': 'Finance_NBFC', 'CANFINHOME': 'Finance_NBFC', 'PNBHOUSING': 'Finance_NBFC', 'POONAWALLA': 'Finance_NBFC',
    'LICI': 'Finance_NBFC', 'MCX': 'Finance_NBFC', 'KFINTECH': 'Finance_NBFC', 'TATASTEEL': 'Metals',
    'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals', 'VEDL': 'Metals', 'NMDC': 'Metals',
    'SAIL': 'Metals', 'JINDALSTEL': 'Metals', 'JSL': 'Metals', 'NATIONALUM': 'Metals',
    'HINDCOPPER': 'Metals', 'MOIL': 'Metals', 'ULTRACEMCO': 'Cement', 'SHREECEM': 'Cement',
    'ACC': 'Cement', 'AMBUJACEM': 'Cement', 'RAMCOCEM': 'Cement', 'DALBHARAT': 'Cement',
    'JKCEMENT': 'Cement', 'NUVOCO': 'Cement', 'BHARTIARTL': 'Telecom', 'INDUSTOWER': 'Telecom',
    'TATACOMM': 'Telecom', 'TTML': 'Telecom', 'HFCL': 'Telecom', 'LT': 'Infrastructure',
    'GRASIM': 'Infrastructure', 'SIEMENS': 'Infrastructure', 'BEL': 'Infrastructure', 'BHARATFORG': 'Infrastructure',
    'BHEL': 'Infrastructure', 'CONCOR': 'Infrastructure', 'GMRAIRPORT': 'Infrastructure', 'DLF': 'Infrastructure',
    'GODREJPROP': 'Infrastructure', 'OBEROIRLTY': 'Infrastructure', 'PRESTIGE': 'Infrastructure', 'BRIGADE': 'Infrastructure',
    'SOBHA': 'Infrastructure', 'IRCTC': 'Infrastructure', 'KEC': 'Infrastructure', 'KALPATPOWR': 'Infrastructure',
    'TITAGARH': 'Industrials', 'TITAN': 'Consumer', 'TRENT': 'Consumer', 'DMART': 'Consumer',
    'JUBLFOOD': 'Consumer', 'INDHOTEL': 'Consumer', 'CROMPTON': 'Consumer', 'VOLTAS': 'Consumer',
    'HAVELLS': 'Consumer', 'POLYCAB': 'Consumer', 'DIXON': 'Consumer', 'WHIRLPOOL': 'Consumer',
    'SAFARI': 'Consumer', 'KALYANKJIL': 'Consumer', 'METROBRAND': 'Consumer', 'PIDILITIND': 'Chemicals',
    'SRF': 'Chemicals', 'NAVINFLUOR': 'Chemicals', 'PIIND': 'Chemicals', 'ATUL': 'Chemicals',
    'DEEPAKNTR': 'Chemicals', 'ALKYLAMINE': 'Chemicals', 'CHAMBLFERT': 'Chemicals', 'VINATIORGA': 'Chemicals',
    'SUMICHEM': 'Chemicals', 'RALLIS': 'Chemicals', 'GSFC': 'Chemicals', 'PURVA': 'Realty',
    'KOLTEPATIL': 'Realty', 'IBREALEST': 'Realty', 'PHOENIXLTD': 'Realty', 'OMAXE': 'Realty',
    'ASIANPAINT': 'Paints', 'BERGEPAINT': 'Paints', 'KANSAINER': 'Paints', 'INDIGOPNTS': 'Paints',
    'CUMMINSIND': 'Industrials', 'HONAUT': 'Industrials', 'SUPREMEIND': 'Industrials', 'BLUESTARCO': 'Industrials',
    'ELGIEQUIP': 'Industrials', 'GRINDWELL': 'Industrials', 'FINCABLES': 'Industrials', 'FINPIPE': 'Industrials',
    'PRINCEPIPE': 'Industrials', 'WABAG': 'Industrials', 'CARBORUNIV': 'Industrials', 'TIMKEN': 'Industrials',
    'SKFINDIA': 'Industrials', 'SCHAEFFLER': 'Industrials', 'JBMA': 'Industrials', 'FORCEMOT': 'Industrials',
    'ZFCVINDIA': 'Industrials', 'JTEKTINDIA': 'Industrials', 'SUBROS': 'Industrials', 'ENGINERSIN': 'Industrials',
    'POWERMECH': 'Industrials', 'PARADEEP': 'Industrials', 'ISGEC': 'Industrials', 'AVALON': 'Industrials',
    'EXICOM': 'Industrials', 'POLYMED': 'Industrials', 'KIRLPNU': 'Industrials', 'IONEXCHANG': 'Industrials',
    'TARSONS': 'Industrials', 'MTAR': 'Industrials', 'DATAPATTNS': 'Industrials', 'NESCO': 'Industrials',
    'TIINDIA': 'Industrials', 'GHCL': 'Industrials', 'VOLTAMP': 'Industrials', 'WELENT': 'Industrials',
    'HUDCO': 'Infrastructure', 'NBCC': 'Infrastructure', 'RAILTEL': 'Infrastructure', 'RITES': 'Infrastructure',
    'NCC': 'Infrastructure', 'KNRCON': 'Infrastructure', 'KPIL': 'Infrastructure', 'LLOYDSENGG': 'Infrastructure',
    'GPPL': 'Infrastructure', 'HBLPOWER': 'Infrastructure', 'GMR': 'Infrastructure', 'JKLAKSHMI': 'Infrastructure',
    'TORNTPOWER': 'Energy', 'NLCINDIA': 'Energy', 'OLECTRA': 'Energy', 'KIRLOSENG': 'Energy',
    'SUZLON': 'Energy', 'UPL': 'Chemicals', 'DHANUKA': 'Chemicals', 'BAYERCROP': 'Chemicals',
    'EIDPARRY': 'Chemicals', 'BALRAMCHIN': 'Chemicals', 'AVANTIFEED': 'Chemicals', 'TATACHEM': 'Chemicals',
    'NOCIL': 'Chemicals', 'ROSSARI': 'Chemicals', 'CLEAN': 'Chemicals', 'ESTER': 'Chemicals',
    'STYRENIX': 'Chemicals', 'RAIN': 'Chemicals', 'KSCL': 'Chemicals', 'BALUARTE': 'Chemicals',
    'ALOKINDS': 'Consumer', 'ARVINDFASN': 'Consumer', 'GOKEX': 'Consumer', 'RAYMOND': 'Consumer',
    'VMART': 'Consumer', 'VIP': 'Consumer', 'VIPIND': 'Consumer', 'WESTLIFE': 'Consumer',
    'ZYDUSWELL': 'Consumer', 'RADICO': 'Consumer', 'JYOTHYLAB': 'Consumer', 'PCJEWELLER': 'Consumer',
    'SHOPERSTOP': 'Consumer', 'VAIBHAVGBL': 'Consumer', 'TASTYBITE': 'Consumer', 'VSTIND': 'Consumer',
    'MCDOWELL-N': 'Consumer', 'PGHH': 'Consumer', 'PEL': 'Consumer', 'GODREJIND': 'Consumer',
    'ABIRLANUVO': 'Consumer', 'RBA': 'Consumer', 'EASEMYTRIP': 'Consumer', 'DELTACORP': 'Consumer',
    'EVEREADY': 'Consumer', 'CASTROLIND': 'Consumer', 'MEDPLUS': 'Consumer', 'FIVESTAR': 'Consumer',
    'INDIGO': 'Consumer', 'VIJAYA': 'Consumer', 'LEMONTREE': 'Consumer', 'CHALET': 'Consumer',
    'INDIACEM': 'Cement', 'ORIENTCEM': 'Cement', 'WELCORP': 'Metals', 'RATNAMANI': 'Metals',
    'SHYAMMETL': 'Metals', 'TINPLATE': 'Metals', 'USHAMART': 'Metals', 'GALLANTT': 'Metals',
    'APLAPOLLO': 'Metals', 'JINDALSAW': 'Metals', 'HIKAL': 'Pharma', 'JBCHEPHARM': 'Pharma',
    'JUBILANT': 'Pharma', 'SHILPAMED': 'Pharma', 'SOLARA': 'Pharma', 'SUVEN': 'Pharma',
    'THYROCARE': 'Pharma', 'SEQUENT': 'Pharma', 'INDSWFTLAB': 'Pharma', 'HONASA': 'FMCG',
    'PARAS': 'Industrials', 'YATHARTH': 'Pharma', 'AXISCADES': 'IT', 'ONWARDTEC': 'IT',
    'INFIBEAM': 'IT', 'ROUTE': 'IT', 'SAREGAMA': 'IT', 'MKCL': 'IT',
    'ZENTEC': 'IT', 'ZOMATO': 'IT', 'JMFINANCIL': 'Finance_NBFC', 'IIFL': 'Finance_NBFC',
    'IIFLSEC': 'Finance_NBFC', 'PAISALO': 'Finance_NBFC', 'SBFC': 'Finance_NBFC', 'MASFIN': 'Finance_NBFC',
    'MMTC': 'Finance_NBFC', 'IFCI': 'Finance_NBFC', 'SPANDANA': 'Finance_NBFC', 'IEX': 'Finance_NBFC',
    'CRISIL': 'Finance_NBFC', 'JUSTDIAL': 'Finance_NBFC', 'REDINGTON': 'Finance_NBFC', 'APTUS': 'Finance_NBFC',
    'ZEEL': 'Media', 'SUNTV': 'Media', 'NETWORK18': 'Media', 'PVRINOX': 'Media',
    'CENTURYTEX': 'Diversified', 'CERA': 'Industrials', 'LUXIND': 'Consumer', 'LOTUSCHOCO': 'Consumer',
    'PRSMJOHNSN': 'Consumer', 'RAJRATAN': 'Industrials', 'MISHTANN': 'Consumer', 'NILKAMAL': 'Consumer',
    'ORIENTELEC': 'Consumer', 'HINDWAREAP': 'Consumer', 'IFBIND': 'Consumer', 'SUPRIYA': 'Pharma',
    'AVANTI': 'Chemicals', 'KRBL': 'Consumer', 'SONACOMS': 'Auto', 'BANKINDIA': 'Banking',
    'CENTRALBK': 'Banking', 'IOB': 'Banking', 'J&KBANK': 'Banking', 'MAHABANK': 'Banking',
    'RBLBANK': 'Banking', 'YESBANK': 'Banking', 'BSOFT': 'IT', 'CAMS': 'IT',
    'FSL': 'IT', 'ITI': 'IT', 'KAYNES': 'IT', 'KPITTECH': 'IT',
    'MAPMYINDIA': 'IT', 'NETWEB': 'IT', 'PAYTM': 'IT', 'PGEL': 'IT',
    'SONATSOFTW': 'IT', 'SYRMA': 'IT', 'TATATECH': 'IT', 'TEJASNET': 'IT',
    'ZENSARTECH': 'IT', 'AKUMS': 'Pharma', 'ALIVUS': 'Pharma', 'APLLTD': 'Pharma',
    'ASTERDM': 'Pharma', 'ASTRAZEN': 'Pharma', 'CAPLIPOINT': 'Pharma', 'COHANCE': 'Pharma',
    'CONCORDBIO': 'Pharma', 'EMCURE': 'Pharma', 'ERIS': 'Pharma', 'GLAND': 'Pharma',
    'IKS': 'Pharma', 'INDGN': 'Pharma', 'JUBLPHARMA': 'Pharma', 'MANKIND': 'Pharma',
    'MEDANTA': 'Pharma', 'NEULANDLAB': 'Pharma', 'NH': 'Pharma', 'PFIZER': 'Pharma',
    'PPLPHARMA': 'Pharma', 'RAINBOW': 'Pharma', 'SAGILITY': 'Pharma', 'SAILIFE': 'Pharma',
    'SYNGENE': 'Pharma', 'WOCKPHARMA': 'Pharma', '360ONE': 'Finance_NBFC', 'AADHARHFC': 'Finance_NBFC',
    'AAVAS': 'Finance_NBFC', 'ABCAPITAL': 'Finance_NBFC', 'ABSLAMC': 'Finance_NBFC', 'AIIL': 'Finance_NBFC',
    'ANANDRATHI': 'Finance_NBFC', 'BAJAJHFL': 'Finance_NBFC', 'BSE': 'Finance_NBFC', 'CDSL': 'Finance_NBFC',
    'CGCL': 'Finance_NBFC', 'CHOLAHLDNG': 'Finance_NBFC', 'CREDITACC': 'Finance_NBFC', 'GICRE': 'Finance_NBFC',
    'GODIGIT': 'Finance_NBFC', 'HOMEFIRST': 'Finance_NBFC', 'IREDA': 'Finance_NBFC', 'IRFC': 'Finance_NBFC',
    'JIOFIN': 'Finance_NBFC', 'LTF': 'Finance_NBFC', 'M&MFIN': 'Finance_NBFC', 'NAM-INDIA': 'Finance_NBFC',
    'NIACL': 'Finance_NBFC', 'NIVABUPA': 'Finance_NBFC', 'NUVAMA': 'Finance_NBFC', 'POLICYBZR': 'Finance_NBFC',
    'SAMMAANCAP': 'Finance_NBFC', 'SHRIRAMFIN': 'Finance_NBFC', 'SUNDARMFIN': 'Finance_NBFC', 'TATAINVEST': 'Finance_NBFC',
    'UTIAMC': 'Finance_NBFC', 'ABB': 'Industrials', 'AIAENG': 'Industrials', 'APARINDS': 'Industrials',
    'ARE&M': 'Industrials', 'BDL': 'Industrials', 'BLS': 'Industrials', 'CGPOWER': 'Industrials',
    'COCHINSHIP': 'Industrials', 'DOMS': 'Industrials', 'ELECON': 'Industrials', 'GRAPHITE': 'Industrials',
    'GRSE': 'Industrials', 'GVT&D': 'Industrials', 'HAL': 'Industrials', 'HBLENGINE': 'Industrials',
    'HEG': 'Industrials', 'INOXINDIA': 'Industrials', 'INOXWIND': 'Industrials', 'IRB': 'Industrials',
    'JWL': 'Industrials', 'JYOTICNC': 'Industrials', 'KEI': 'Industrials', 'KIRLOSBROS': 'Industrials',
    'LATENTVIEW': 'Industrials', 'MAZDOCK': 'Industrials', 'POWERINDIA': 'Industrials', 'RRKABEL': 'Industrials',
    'SCHNEIDER': 'Industrials', 'TARIL': 'Industrials', 'TRITURBINE': 'Industrials', 'VGUARD': 'Industrials',
    'ABFRL': 'Consumer', 'AMBER': 'Consumer', 'ASTRAL': 'Consumer', 'CAMPUS': 'Consumer',
    'CENTURYPLY': 'Consumer', 'DEVYANI': 'Consumer', 'EIHOTEL': 'Consumer', 'ETERNAL': 'Consumer',
    'FIRSTCRY': 'Consumer', 'KAJARIACER': 'Consumer', 'KPRMILL': 'Consumer', 'MANYAVAR': 'Consumer',
    'NYKAA': 'Consumer', 'RAYMONDLSL': 'Consumer', 'RTNINDIA': 'Consumer', 'SAPPHIRE': 'Consumer',
    'SWIGGY': 'Consumer', 'TBOTEK': 'Consumer', 'TRIDENT': 'Consumer', 'VMM': 'Consumer',
    'VTL': 'Consumer', 'WELSPUNLIV': 'Consumer', 'APOLLOTYRE': 'Auto', 'ASAHIINDIA': 'Auto',
    'BALKRISIND': 'Auto', 'CRAFTSMAN': 'Auto', 'HYUNDAI': 'Auto', 'JKTYRE': 'Auto',
    'MINDACORP': 'Auto', 'MSUMI': 'Auto', 'OLAELEC': 'Auto', 'SUNDRMFAST': 'Auto',
    'AWL': 'FMCG', 'BBTC': 'FMCG', 'CCL': 'FMCG', 'GILLETTE': 'FMCG',
    'GODFRYPHLP': 'FMCG', 'GODREJAGRO': 'FMCG', 'LTFOODS': 'FMCG', 'PATANJALI': 'FMCG',
    'RENUKA': 'FMCG', 'TRIVENI': 'FMCG', 'UNITDSPR': 'FMCG', 'ACMESOLAR': 'Energy',
    'AEGISLOG': 'Energy', 'ATGL': 'Energy', 'CESC': 'Energy', 'CHENNPETRO': 'Energy',
    'GMDCLTD': 'Energy', 'JPPOWER': 'Energy', 'MRPL': 'Energy', 'NHPC': 'Energy',
    'NTPCGREEN': 'Energy', 'OIL': 'Energy', 'PREMIERENE': 'Energy', 'RPOWER': 'Energy',
    'SJVN': 'Energy', 'SWSOLAR': 'Energy', 'WAAREEENER': 'Energy', 'AARTIIND': 'Chemicals',
    'BASF': 'Chemicals', 'COROMANDEL': 'Chemicals', 'DEEPAKFERT': 'Chemicals', 'FACT': 'Chemicals',
    'FLUOROCHEM': 'Chemicals', 'GNFC': 'Chemicals', 'HSCL': 'Chemicals', 'JUBLINGREA': 'Chemicals',
    'LINDEINDIA': 'Chemicals', 'PCBL': 'Chemicals', 'RCF': 'Chemicals', 'SOLARINDS': 'Chemicals',
    'GPIL': 'Metals', 'GRAVITA': 'Metals', 'HINDZINC': 'Metals', 'IGIL': 'Metals',
    'LLOYDSME': 'Metals', 'MAHSEAMLES': 'Metals', 'NSLNISP': 'Metals', 'PTCIL': 'Metals',
    'RHIM': 'Metals', 'RKFORGE': 'Metals', 'SARDAEN': 'Metals', 'ACE': 'Infrastructure',
    'AFCONS': 'Infrastructure', 'ASHOKLEY': 'Infrastructure', 'BLUEDART': 'Infrastructure', 'DELHIVERY': 'Infrastructure',
    'GESHIP': 'Infrastructure', 'IRCON': 'Infrastructure', 'JSWINFRA': 'Infrastructure', 'PNCINFRA': 'Infrastructure',
    'PRAJIND': 'Infrastructure', 'RVNL': 'Infrastructure', 'SCI': 'Infrastructure', 'TECHNOE': 'Infrastructure',
    'BHARTIHEXA': 'Telecom', 'IDEA': 'Telecom', 'ABREL': 'Realty', 'ANANTRAJ': 'Realty',
    'DBREALTY': 'Realty', 'LODHA': 'Realty', 'SIGNATURE': 'Realty', '3MINDIA': 'Diversified',
    'BEML': 'Diversified', 'CYIENT': 'Diversified', 'DCMSHRIRAM': 'Diversified', 'JSWHL': 'Diversified',
    'NAVA': 'Diversified', 'SWANENERGY': 'Diversified', 'THERMAX': 'Diversified',
}



def get_sector(ticker: str) -> str:
    """Sector label for ``ticker`` (``SECTOR_MAP``), defaulting to ``'Others'``."""
    return SECTOR_MAP.get(ticker, "Others")
