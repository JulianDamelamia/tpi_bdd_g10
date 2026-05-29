from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class EtlProcessExecution(Base):
    __tablename__ = "etl_process_executions"

    process_execution_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    process_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    process_from: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    process_to: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    environment: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_loaded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
