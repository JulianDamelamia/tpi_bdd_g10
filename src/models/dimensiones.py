from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class DimSurvey(Base):
    __tablename__ = "dim_surveys"

    survey_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    creator_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    topic: Mapped[str] = mapped_column(String(80), nullable=False)

    questions: Mapped[list["DimQuestion"]] = relationship(
        back_populates="survey",
        cascade="all, delete-orphan",
    )
    responses: Mapped[list["FactSurveyResponse"]] = relationship(back_populates="survey")


class DimQuestion(Base):
    __tablename__ = "dim_questions"

    question_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    survey_id: Mapped[str] = mapped_column(
        ForeignKey("dim_surveys.survey_id"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)

    survey: Mapped["DimSurvey"] = relationship(back_populates="questions")
    options: Mapped[list["DimAnswerOption"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )
    responses: Mapped[list["FactSurveyResponse"]] = relationship(back_populates="question")


class DimTime(Base):
    __tablename__ = "dim_time"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_date: Mapped[dt.date] = mapped_column(Date, nullable=False, unique=True)
    day_of_week: Mapped[str] = mapped_column(String(15), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[str] = mapped_column(String(15), nullable=False)
    month_number: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    responses: Mapped[list["FactSurveyResponse"]] = relationship(back_populates="time")


class DimAnswerOption(Base):
    __tablename__ = "dim_answer_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_code", name="uq_answer_option_question_code"),
    )

    option_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    question_id: Mapped[str] = mapped_column(
        ForeignKey("dim_questions.question_id"),
        nullable=False,
        index=True,
    )
    option_code: Mapped[int] = mapped_column(Integer, nullable=False)
    option_text: Mapped[str] = mapped_column(String(300), nullable=False)

    question: Mapped["DimQuestion"] = relationship(back_populates="options")
    responses: Mapped[list["FactSurveyResponse"]] = relationship(back_populates="answer_option")
