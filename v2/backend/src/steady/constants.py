"""Every fixed name and message in one place."""

SERVICE_NAME = "steady"
API_PREFIX = "/api"
DOCS_PATH = f"{API_PREFIX}/docs"
OPENAPI_PATH = f"{API_PREFIX}/openapi.json"
HEALTH_PATH = "/health"

ENV_PREFIX = "STEADY_"
DEFAULT_VERSION = "dev"
INDEX_FILE = "index.html"
STATUS_OK = "ok"

GZIP_MINIMUM_BYTES = 1024
ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

MSG_NOT_FOUND = "Not found"
MSG_INTERFACE_NOT_BUILT = "Interface is not built"

# --- stock metrics (v2/docs/DESIGN.md section 3) ---
REFERENCE_WINDOW_DAYS = 126
MIN_HISTORY_DAYS = 60
FALL_PCT = 10.0
RECOVERY_WITHIN_DAYS = 252
OPEN_FALL_LIMIT_DAYS = 126
MIN_FALLS_TO_JUDGE = 5
BUY_LEVELS_PCT = (10.0, 20.0, 30.0)
HARD_EXIT_PCT = 40.0
TRADING_DAYS_PER_YEAR = 252

# --- scores ---
STABILITY_WEIGHTS = {
    "quick": 35.0,
    "no_long": 20.0,
    "nothing_open": 15.0,
    "shallow": 15.0,
    "history": 15.0,
}
QUICK_RECOVERY_RANGE = (50.0, 90.0)
LONGEST_RECOVERY_RANGE = (756.0, 252.0)
DRAWDOWN_RANGE = (70.0, 30.0)
HISTORY_YEARS_RANGE = (3.0, 8.0)
FINANCIAL_WEIGHTS = {
    "revenue": 20.0,
    "profit_every_year": 25.0,
    "profit_growth": 20.0,
    "debt": 20.0,
    "pledge": 15.0,
}
FINANCIAL_YEARS = 5
MAX_DEBT_TO_EQUITY = 1.0
EVIDENCE_WEIGHTS = (0.5, 0.3, 0.2)
DATA_PROBLEM_PENALTY = 20.0

NEED_FEW_FALLS = "Few past falls to judge recovery"
NEED_SHORT_HISTORY = "Fewer than 8 years of price history"
NEED_REVENUE_YEARS = "Five years of revenue"
NEED_PROFIT_YEARS = "Five years of net profit"
NEED_PROFIT_ENDS = "Net profit for the first and latest year"
NEED_DEBT = "Debt and equity"
NEED_PLEDGE = "Promoter pledge"

# --- stocks service ---
STOCKS_PATH = "/stocks"
METRICS_START = "2016-01-01"
PRICE_HISTORY_START = "2015-06-01"
PRICE_TTL_SECONDS = 1800
STALE_AFTER_DAYS = 4
HISTORY_SAMPLE_DAYS = 250
HISTORY_SAMPLE_STEP = 5
MAX_FETCH_WORKERS = 6
SEED_FILE = "stocks.json"

NEED_OFFICIAL_PRICES = "Official price feed (currently a public source)"
NEED_LOT_SIZE = "Futures lot size"
NEED_FRESH_PRICES = "Fresh prices (the latest is more than 4 days old)"
NEED_PRICE_HISTORY = "Price history (the price source did not answer)"
MSG_UNKNOWN_STOCK = "Unknown stock"

# --- public price source (unofficial; replaced by a broker feed later) ---
YAHOO_NAME = "Yahoo Finance daily close (unofficial)"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
YAHOO_USER_AGENT = "Mozilla/5.0 (compatible; steady/0.1)"
YAHOO_TIMEOUT_SECONDS = 15.0
PRICE_FETCH_ATTEMPTS = 2
MARKET_UTC_OFFSET_MINUTES = 330
