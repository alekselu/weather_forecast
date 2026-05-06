from sqlalchemy import Column, Integer, String, Float
from app.db.base import Base


class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
