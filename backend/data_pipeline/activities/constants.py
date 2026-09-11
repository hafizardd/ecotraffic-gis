from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_DIR / "data"
DEFAULT_INPUT = DEFAULT_DATA_DIR / "output" / "activities.csv"

SOURCE_TYPE = "survey_activity"
SOURCE_FILE_NAME = "raw/activities_raw.csv"
EXTRACTION_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
EXTRACTION_VERSION = "activities-v1"
SCHEMA_VERSION = "activities-schema-v1"
PROMPT_VERSION = "activities-prompt-v2"

TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503})
NON_RETRYABLE_HTTP_STATUSES = frozenset({401, 402, 403})

PASSENGER_LEVELS = ("very_low", "low", "moderate", "high", "very_high", "unknown")
ACCESS_LEVELS = ("good", "moderate", "poor", "unknown")
CONDITION_LEVELS = ("excellent", "good", "moderate", "poor", "very_poor", "unknown")
ISSUE_CATEGORIES = (
    "cleanliness", "maintenance", "accessibility", "pedestrian", "lighting",
    "signage", "facility", "safety", "parking", "traffic", "environment",
)
ISSUE_SEVERITIES = ("low", "moderate", "high", "unknown")
PLACE_CATEGORIES = (
    "school", "university", "hospital", "market", "park", "tourism",
    "government", "commercial", "residential", "religious",
    "transportation", "office", "hotel", "restaurant",
)
