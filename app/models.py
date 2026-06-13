from sqlalchemy import Column, DateTime, Integer, String, func

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    role = Column(String(120), nullable=False)
    department = Column(String(120), nullable=False, default="Engineering")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)