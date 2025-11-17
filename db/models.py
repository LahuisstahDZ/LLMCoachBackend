from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from db.database import Base

#DATABASE_URL = "postgresql://postgres:madbestlameilleure@localhost:5432/llmcoach_db"
#DATABASE_URL = "postgresql://postgres:WjHb9Udsizul5d0GD5xoAXNgxDksLBvZ@localhost:5432/llmcoach_db"
#DATABASE_URL = "postgresql://llmcoach_db_user:WjHb9Udsizul5d0GD5xoAXNgxDksLBvZ@localhost:5432/llmcoach_db"

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    weeks = relationship("Week", back_populates="user")
    settings = relationship("Settings", back_populates="user")
    social = relationship("Social", back_populates="user")
    

class Week(Base):
    __tablename__ = "week"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    week_number = Column(Integer, nullable = False)
    description = Column(JSONB, default=lambda: {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "sunday": []
    })
    
    user = relationship("User", back_populates="weeks")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    personal_goals = Column(ARRAY(String), default=list)
    coach_preferences = Column(JSONB, default = lambda:{})
    training_goals = Column(JSONB, default = lambda:{})
    user = relationship("User", back_populates="settings")

class Social(Base):
    __tablename__ = "social"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    friends = Column(ARRAY(Integer, ForeignKey("user.id")), default=lambda:{})
    rewards = Column(JSONB, default = lambda:{})
    
    user = relationship("User", back_populates="social")

    