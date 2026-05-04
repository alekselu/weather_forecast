from sqlalchemy import Column, Integer, Float, Date, String
from app.db.base import Base


class WeatherDaily(Base):
    __tablename__ = "weather_daily"

    id = Column(Integer, primary_key=True)
    city = Column(String, index=True)
    date = Column(Date, index=True)

    temperature_mean = Column(Float)
    temperature_min = Column(Float)
    temperature_max = Column(Float)

    precipitation_sum = Column(Float)
    wind_speed = Column(Float)
    pressure = Column(Float)
    humidity = Column(Float)
