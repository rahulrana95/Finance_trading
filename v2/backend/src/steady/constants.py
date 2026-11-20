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
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_STOCK_SUFFIX = ".NS"
INDEX_PREFIX = "^"
YAHOO_USER_AGENT = "Mozilla/5.0 (compatible; steady/0.1)"
YAHOO_TIMEOUT_SECONDS = 15.0
PRICE_FETCH_ATTEMPTS = 2
MARKET_UTC_OFFSET_MINUTES = 330

# --- plan and paper settings (v2/docs/DESIGN.md section 3.6; PRD decisions D6, D7) ---
PAPER_CAPITAL = 2_000_000
PER_STOCK_CAP_PCT = 20.0
PLAN_PARTS = (1, 2, 3)
FUTURES_FROM_STEP = 3
INSTRUMENT_CASH = "cash"
INSTRUMENT_FUTURE = "future"
TYPE_COMBO = "combo"
STATUS_APPROVED = "approved"

NOTE_FUTURES_FROM = "Futures are only considered from step {step}."
NOTE_LOT_UNKNOWN = "Futures not offered: lot size needs data."
NOTE_LOT_TOO_BIG = (
    "Futures not offered: one lot is worth about {lot}, more than the {amount} for this step."
)
NOTE_FUTURES_USED = "Step {step} uses one futures lot."

# --- algo runs and ideas ---
RUNS_PATH = "/runs"
IDEAS_PATH = "/recommendations"
MAX_RUNS_KEPT = 50
KIND_SCHEDULED = "scheduled"
KIND_ON_DEMAND = "on_demand"
KIND_DRY_RUN = "dry_run"
RUN_RUNNING = "running"
RUN_DONE = "done"
RUN_FAILED = "failed"
IDEA_NEW = "new"
IDEA_EXPIRED = "expired"
LEVEL_OK = "ok"
LEVEL_INFO = "info"
LEVEL_ACTION = "action"
LEVEL_WARN = "warn"
LEVEL_ERROR = "error"
MSG_UNKNOWN_RUN = "Unknown run"
SUMMARY_RUNNING = "Running"
SUMMARY_NO_ACTION = "No action"
SUMMARY_DRY_RUN = "Dry run, no ideas created"
SUMMARY_NO_PRICES = "No prices available"
SUMMARY_FAILED = "The run failed"

# --- schedule (India time; exchange holidays are not known yet) ---
MARKET_TIMEZONE = "Asia/Kolkata"
MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)
SCHEDULE_DAYS = "mon-fri"
SCHEDULE_HOURS = "9-15"
SCHEDULE_MINUTES = "*/5"
SCHEDULER_JOB_ID = "algo-run"
SCHEDULER_START_JOB_ID = "algo-run-at-start"

# --- database ---
POSTGRES_PREFIXES = ("postgres://", "postgresql://")
POSTGRES_DRIVER_PREFIX = "postgresql+psycopg://"
SQLITE_PREFIX = "sqlite"
SUMMARY_INTERRUPTED = "Interrupted by a restart"

# --- market-fall screener (rules from research logged 2026-11-20 in BACKTEST_RESULTS.md) ---
SCREENS_PATH = "/screens"
UNIVERSE_FILE = "nifty500.json"
MARKET_SYMBOL = "^NSEI"
SCREEN_WINDOW_DAYS = 252  # falls are measured from the 1-year high
SCREEN_MIN_HISTORY = 120
SCREEN_LEVELS_PCT = (20.0, 25.0, 30.0, 40.0)
SCREEN_REARM_PCT = 10.0  # a new fall counts only after the stock was back within 10% of its high
MARKET_DOWN_PCT = 10.0  # "the whole market fell": the index is this far below its 1-year high
MARKET_DEEP_PCT = 15.0  # a deep market fall: the case with the best record
MARKET_FINE, MARKET_DOWN, MARKET_DEEP = "fine", "down", "deep"
MARKET_STATES = (MARKET_DEEP, MARKET_DOWN, MARKET_FINE)
CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW = "high", "medium", "low"
CONFIDENCE_ORDER = {CONFIDENCE_HIGH: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_LOW: 2}
HIGH_MIN_LEVEL_PCT = 25.0
DEMERGER_DROP_PCT = 35.0  # a one-day drop this large is usually a demerger or split
HALF_YEAR_DAYS = 126
YEAR_DAYS = 252
GAIN_6M_PCT = (10.0, 20.0)
GAIN_12M_PCT = 30.0
FURTHER_FALL_PCT = 20.0
SCREEN_WORKERS = 8
SCREEN_MAX_AGE_HOURS = 20
SCREEN_HOUR, SCREEN_MINUTE = 18, 30
SCREENER_JOB_ID = "screener"
SCREENER_START_JOB_ID = "screener-at-start"
