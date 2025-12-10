from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
from db.database import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    weeks = relationship("Week", back_populates="user")
    settings = relationship("Settings", back_populates="user")
    credentials = relationship("Credentials", back_populates="user")
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

class Credentials(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    
    username = Column(String, default="Francesco")
    activity = Column(String, default="")
    gender = Column(String, default = "Female")
    birthdate = Column(Date, nullable=False, server_default=func.now())
    height = Column(String, default="165")
    weight = Column(String, default="70")
    memory = Column(ARRAY(String), default=list)
    
    user = relationship("User", back_populates="credentials")


class Social(Base):
    __tablename__ = "social"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    friends = Column(ARRAY(Integer, ForeignKey("user.id")), default=lambda:{})
    rewards = Column(JSONB, default = lambda:{})
    
    user = relationship("User", back_populates="social")

    