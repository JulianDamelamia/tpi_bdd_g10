from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FactSurveyResponse(Base):
    __tablename__ = "fact_survey_responses"
    __table_args__ = (
        UniqueConstraint("response_id", "question_id", name="uq_fact_response_question"),
    )

    response_row_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    response_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    survey_id: Mapped[str] = mapped_column(
        ForeignKey("dim_surveys.survey_id"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("dim_questions.question_id"),
        nullable=False,
        index=True,
    )
    option_id: Mapped[str | None] = mapped_column(
        ForeignKey("dim_answer_options.option_id"),
        nullable=True,
        index=True,
    )
    respondent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    answer_text: Mapped[str | None] = mapped_column(Text)
    answer_numeric: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    date_key: Mapped[int] = mapped_column(
        ForeignKey("dim_time.date_key"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    submitted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    survey: Mapped["DimSurvey"] = relationship(back_populates="responses")
    question: Mapped["DimQuestion"] = relationship(back_populates="responses")
    answer_option: Mapped["DimAnswerOption"] = relationship(back_populates="responses")
    time: Mapped["DimTime"] = relationship(back_populates="responses")
