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
