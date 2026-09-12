import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SegmentNameEmbedding(Base):
    """Precomputed embedding for one canonical road-segment name group.

    Used only for entity resolution (misspelling/paraphrase matching). The
    vector is stored as a JSONB float array so the small corpus (a few hundred
    rows) can be loaded in-process and compared with cosine in Python; no
    pgvector dependency is required.
    """

    __tablename__ = "road_segment_name_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    road_segment_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list] = mapped_column(JSONB, nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
