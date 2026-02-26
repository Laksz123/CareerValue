from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Float, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    city = Column(String, nullable=True)
    sphere = Column(String, nullable=True)
    experience = Column(String, nullable=True)
    market_value = Column(Float, nullable=True)
    test_completed = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    city = Column(String, nullable=False)
    sphere = Column(String, nullable=False)
    experience = Column(String, nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    link = Column(String, nullable=True)
    description = Column(String, nullable=True)


class VacancyPost(Base):
    __tablename__ = "vacancy_posts"

    id = Column(Integer, primary_key=True)
    content_type = Column(String(10), nullable=False)  # "text" | "photo"
    text = Column(String, nullable=False)
    entities_json = Column(String, nullable=True)
    photo_file_id = Column(String, nullable=True)
    reply_markup_json = Column(String, nullable=True)  # InlineKeyboardMarkup


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class ReferralLink(Base):
    __tablename__ = "referral_links"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
