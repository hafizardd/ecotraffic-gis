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

    # Deployments may define settings for adjacent services; they should not
    # prevent this application from starting when those keys are unrelated.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
