from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    DATABASE_NAME: str
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    REDIS_URL: str = "redis://localhost:6379/0"

    DEBUG: bool = False
    SECRET_KEY: str = "changeme"

    YOLO_MODEL_PATH: str = "yolo/yolov8l.pt"
    CONFIDENCE_THRESHOLD: float = 0.4

    STREAM_REFERER: str = "https://cctv.jogjakota.go.id/"
    INTERVAL_SECONDS: int = 5

    class Config:
        env_file = ".env"

settings = Settings()