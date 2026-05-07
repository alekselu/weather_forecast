from sqlalchemy import Column, Integer, Float, Date, String, Index, ForeignKey
from app.db.base import Base
from sqlalchemy.orm import relationship


class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    id = Column(Integer, primary_key=True)

    # ключи
    city_id = Column(Integer, ForeignKey("cities.id"), nullable=False)
    city = relationship("City")

    date = Column(Date, nullable=False, index=True)

    # температура
    temperature_2m_mean = Column(Float)
    temperature_2m_min = Column(Float)
    temperature_2m_max = Column(Float)

    apparent_temperature_mean = Column(Float)
    apparent_temperature_min = Column(Float)
    apparent_temperature_max = Column(Float)

    # осадки
    precipitation_sum = Column(Float)
    rain_sum = Column(Float)
    snowfall_sum = Column(Float)
    precipitation_hours = Column(Float)

    # атмосфера
    pressure_msl_mean = Column(Float)
    relative_humidity_2m_mean = Column(Float)

    # ветер
    wind_speed_10m_max = Column(Float)
    wind_gusts_10m_max = Column(Float)

    # радиация
    shortwave_radiation_sum = Column(Float)
    sunshine_duration = Column(Float)

    # дополнительное
    uv_index_max = Column(Float)
    daylight_duration = Column(Float)
    weather_code = Column(Integer)

    __table_args__ = (Index("ix_weather_city_date", "city_id", "date"),)
