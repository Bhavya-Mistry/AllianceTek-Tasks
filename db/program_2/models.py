from database import Base
from sqlalchemy import Integer, String, Column

class Books(Base):
    __tablename__="books"

    id=Column(Integer, primary_key=True, nullable=False)
    title=Column(String, nullable=False, unique=True)
    author=Column(String, nullable=False)
    pages=Column(Integer, nullable=False)

