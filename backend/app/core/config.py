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

    YOLO_MODEL_PATH: str = "yolo/yolov8l.pt"
    CONFIDENCE_THRESHOLD: float = 0.4

    STREAM_REFERER: str = "https://cctv.jogjakota.go.id/"

    # Legacy global interval retained for standalone CV utilities and existing
    # deployments. Camera scheduling now uses the priority-specific settings.
    INTERVAL_SECONDS: int = 60

    CAMERA_HIGH_INTERVAL_SECONDS: int = Field(default=10, gt=0)
    CAMERA_MEDIUM_INTERVAL_SECONDS: int = Field(default=60, gt=0)
    CAMERA_LOW_INTERVAL_SECONDS: int = Field(default=60, gt=0)
    CAMERA_SCHEDULER_TICK_SECONDS: int = Field(default=1, gt=0)
    CAMERA_SCHEDULER_MAX_DISPATCH_PER_TICK: int = Field(default=8, gt=0)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
