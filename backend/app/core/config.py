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

    YOLO_MODEL_PATH: str = "yolo/yolo11n.pt"
    YOLO_DEVICE: str = "auto"
    YOLO_IMAGE_SIZE: int = Field(default=512, gt=0)
    CONFIDENCE_THRESHOLD: float = Field(default=0.25, ge=0.0, le=1.0)
    YOLO_TRACKER: str = "bytetrack.yaml"
    YOLO_IOU: float = Field(default=0.5, ge=0.0, le=1.0)
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
    INTERVAL_SECONDS: int = 60

    CAMERA_HIGH_INTERVAL_SECONDS: int = Field(default=10, gt=0)
    CAMERA_MEDIUM_INTERVAL_SECONDS: int = Field(default=60, gt=0)
    CAMERA_LOW_INTERVAL_SECONDS: int = Field(default=60, gt=0)
    CAMERA_SCHEDULER_TICK_SECONDS: int = Field(default=1, gt=0)
    CAMERA_SCHEDULER_MAX_DISPATCH_PER_TICK: int = Field(default=8, gt=0)
    CAMERA_RETRY_BASE_SECONDS: int = Field(default=5, gt=0)
    CAMERA_RETRY_MAX_SECONDS: int = Field(default=60, gt=0)
    CAMERA_FAILURES_BEFORE_OFFLINE: int = Field(default=4, gt=0)
    CAMERA_STALENESS_CHECK_INTERVAL_SECONDS: int = Field(default=30, gt=0)
    CAMERA_OFFLINE_THRESHOLD_SECONDS: int = Field(default=300, gt=0)
    DATA_FRESH_THRESHOLD_SECONDS: int = Field(default=30, ge=0)
    DATA_AGING_THRESHOLD_SECONDS: int = Field(default=90, ge=0)

    FRAME_CAPTURE_OPEN_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    FRAME_CAPTURE_READ_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    FRAME_FFMPEG_TIMEOUT_SECONDS: int = Field(default=30, gt=0)

    INFERENCE_QUEUE_MAX_PENDING: int = Field(default=64, gt=0)
    INFERENCE_RESERVATION_TTL_SECONDS: int = Field(default=180, gt=0)
    INFERENCE_FRAME_TTL_SECONDS: int = Field(default=180, gt=0)
    INFERENCE_FRAME_MAX_BYTES: int = Field(default=2_000_000, gt=0)
    INFERENCE_JPEG_QUALITY: int = Field(default=85, ge=1, le=100)
    INFERENCE_TASK_SOFT_TIME_LIMIT_SECONDS: int = Field(default=90, gt=0)
    INFERENCE_TASK_TIME_LIMIT_SECONDS: int = Field(default=120, gt=0)
    INFERENCE_MAX_RETRIES: int = Field(default=2, ge=0)
    INFERENCE_MAX_BATCH_SIZE: int = Field(default=8, gt=0)
    INFERENCE_MAX_BATCH_WAIT_MS: int = Field(default=200, ge=0)
    INFERENCE_BATCH_RESULT_TIMEOUT_SECONDS: int = Field(default=80, gt=0)
    INFERENCE_WORKER_CONCURRENCY: int = Field(default=8, gt=0)

    EMISSION_AGGREGATION_WINDOW_SECONDS: int = Field(default=60, gt=0)
    LATEST_EMISSION_STATE_TTL_SECONDS: int = Field(default=3600, gt=0)

    SEGMENT_CALCULATION_PERIOD_MINUTES: int = Field(default=1, gt=0)
    SEGMENT_OBSERVATION_WINDOW_SECONDS: int = Field(default=60, gt=0)
    SEGMENT_MAPPING_CACHE_TTL_SECONDS: int = Field(default=300, gt=0)
    SEGMENT_LATEST_STATE_TTL_SECONDS: int = Field(default=3600, gt=0)
    K3_BUFFER_DISTANCE_M: int = Field(default=400, gt=0)
    K4_BUFFER_DISTANCE_M: int = Field(default=500, gt=0)
    K5_BUFFER_DISTANCE_M: int = Field(default=500, gt=0)

    # Deployments may define settings for adjacent services; they should not
    # prevent this application from starting when those keys are unrelated.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
