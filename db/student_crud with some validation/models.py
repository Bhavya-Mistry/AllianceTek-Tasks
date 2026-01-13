from database import Base
from sqlalchemy import Column, Integer, String


class Student(Base):
    __tablename__ = "student"

    id=Column(Integer, primary_key=True)
    name=Column(String, nullable=False)
    email=Column(String, nullable=False, unique=True)
    age=Column(Integer, nullable=False)