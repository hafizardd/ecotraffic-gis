from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    REDIS_URL: str 

    DEBUG: bool = False
    SECRET_KEY: str 

    YOLO_MODEL_PATH: str = "yolo/best30.pt"
    YOLO_DEVICE: str = "auto"
    YOLO_IMAGE_SIZE: int = Field(default=512, gt=0)
    CONFIDENCE_THRESHOLD: float = Field(default=0.25, ge=0.0, le=1.0)
    YOLO_TRACKER: str = "bytetrack.yaml"
    YOLO_IOU: float = Field(default=0.7, ge=0.0, le=1.0)
    TRACK_FPS: float = Field(default=5.0, gt=0)
    TRACK_CAMS: str = "atcs_jlagran,atcs_balaikota_timur"
    TRACK_FLOW_MIN_FRAMES: int = Field(default=3, gt=0)
    TRACK_FLOW_EXIT_FRAMES: int = Field(default=5, gt=0)
    TRACK_DB_FLUSH_SECONDS: int = Field(default=60, gt=0)
    TRACK_SNAPSHOT_TTL_SECONDS: int = Field(default=180, gt=0)
    # Annotated MJPEG display stream: the tracking worker writes annotated
    # JPEGs to tracks:snapshot:{id}; the /tracked.mjpg endpoint polls that key.
    STREAM_JPEG_QUALITY: int = Field(default=70, ge=1, le=100)
    STREAM_FPS: float = Field(default=5.0, gt=0)

    STREAM_REFERER: str = "https://cctv.jogjakota.go.id/"

    # Legacy global interval retained for standalone CV utilities and existing
    # deployments. Camera scheduling now uses the priority-specific settings.
    DATA_FRESH_THRESHOLD_SECONDS: int = Field(default=30, ge=0)
    DATA_AGING_THRESHOLD_SECONDS: int = Field(default=90, ge=0)

    # Retained: still used by tracker capture + on-demand JPEG path.
    FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    FRAME_CAPTURE_READ_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    FRAME_FFMPEG_TIMEOUT_SECONDS: int = Field(default=30, gt=0)
    INFERENCE_FRAME_MAX_BYTES: int = Field(default=2_000_000, gt=0)

    EMISSION_AGGREGATION_WINDOW_SECONDS: int = Field(default=60, gt=0)
    LATEST_EMISSION_STATE_TTL_SECONDS: int = Field(default=3600, gt=0)

    # Deprecated compatibility setting. Beat follows the observation window.
    SEGMENT_CALCULATION_PERIOD_MINUTES: int = Field(default=1, gt=0)
    SEGMENT_OBSERVATION_WINDOW_SECONDS: int = Field(default=60, gt=0)
    SEGMENT_MAPPING_CACHE_TTL_SECONDS: int = Field(default=300, gt=0)
    SEGMENT_LATEST_STATE_TTL_SECONDS: int = Field(default=3600, gt=0)
    K3_BUFFER_DISTANCE_M: int = Field(default=400, gt=0)
    K4_BUFFER_DISTANCE_M: int = Field(default=500, gt=0)
    K5_BUFFER_DISTANCE_M: int = Field(default=500, gt=0)

    # Historical snapshot sampler: one frame per camera per cycle, batched.
    # Priority intervals default to the relaxed cadence; boost via env during
    # the first ~24h backfill (SNAPSHOT_HIGH/MEDIUM/LOW_INTERVAL_SECONDS).
    SNAPSHOT_HIGH_INTERVAL_SECONDS: int = Field(default=900, gt=0)
    SNAPSHOT_MEDIUM_INTERVAL_SECONDS: int = Field(default=1800, gt=0)
    SNAPSHOT_LOW_INTERVAL_SECONDS: int = Field(default=3600, gt=0)
    SNAPSHOT_CLAIM_BATCH_SIZE: int = Field(default=12, gt=0)
    SNAPSHOT_CHUNK_SIZE: int = Field(default=10, gt=0)
    SNAPSHOT_FAILURES_BEFORE_OFFLINE: int = Field(default=5, gt=0)
    SNAPSHOT_DRY_RUN: bool = False

    # Bang Jo assistant (Groq, OpenAI-compatible). Answers are always
    # LLM-authored markdown; when the model is unavailable the route returns a
    # retryable 502 instead of a synthesized fallback.
    GROQ_API_KEY: str | None = None
    BANGJO_MODEL: str = "openai/gpt-oss-120b"
    BANGJO_BASE_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    # Generous so a reasoning-capable model still has room after hidden thinking.
    # The effective output allowance is lowered automatically to keep
    # input + output under BANGJO_REQUEST_TOKEN_LIMIT.
    BANGJO_MAX_TOKENS: int = Field(default=2048, gt=0)
    # Groq's free tier counts prompt tokens AND requested max_tokens against the
    # per-minute limit, which is also a hard per-request ceiling (HTTP 413).
    BANGJO_REQUEST_TOKEN_LIMIT: int = Field(default=8000, gt=0)
    BANGJO_MIN_TOKENS: int = Field(default=512, gt=0)
    BANGJO_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    BANGJO_DEBUG_RAW: bool = False

    # Groq reasoning controls. Leave both unset for a plain instruct model (the
    # recommended default): there is no chain-of-thought to leak. For a
    # reasoning-capable Groq model set BANGJO_REASONING_FORMAT="hidden" (or
    # "parsed" to keep the trace in a separate field for logging) and a
    # model-appropriate BANGJO_REASONING_EFFORT. "hidden" suppresses the
    # reasoning text but the model may still spend tokens reasoning internally.
    BANGJO_REASONING_FORMAT: str | None = None
    BANGJO_REASONING_EFFORT: str | None = None

    # Optional secondary model/provider. When set, a single retryable failure
    # (429/5xx/timeout) on the primary is retried once here before failing.
    # Base URL/key default to the primary Groq provider.
    BANGJO_FALLBACK_MODEL: str | None = "openai/gpt-oss-120b"
    BANGJO_FALLBACK_BASE_URL: str | None = None
    BANGJO_FALLBACK_API_KEY: str | None = None

    # Entity-resolution embeddings (OpenRouter-compatible /embeddings) still use
    # OpenRouter + httpx; every failure falls back to string matching.
    OPENROUTER_API_KEY: str | None = None
    BANGJO_EMBEDDINGS_ENABLED: bool = True
    BANGJO_EMBEDDING_MODEL: str = "openai/text-embedding-3-small"
    BANGJO_EMBEDDINGS_URL: str = "https://openrouter.ai/api/v1/embeddings"
    BANGJO_RESOLUTION_THRESHOLD: float = Field(default=0.82, ge=0.0, le=1.0)
    BANGJO_AUTOINSIGHT_TTL_SECONDS: int = Field(default=300, gt=0)
    BANGJO_CACHE_TTL_SECONDS: int = Field(default=300, gt=0)

    # Deployments may define settings for adjacent services; they should not
    # prevent this application from starting when those keys are unrelated.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
