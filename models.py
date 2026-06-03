from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Table association for user and group classes 
group_members=Table(
    "group_members",
    Base.metadata, 
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"),primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"),primary_key=True)
)


class User(Base):
    __tablename__="users"

    id=Column(Integer, primary_key=True, index=True)
    name= Column(String, nullable=False)
    email= Column(String, unique=True, index=True, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

    groups=relationship("Group",secondary=group_members, back_populates="members")  
    expenses_paid= relationship("Expense", back_populates="payer")     #one to many

class Group(Base):
    __tablename__="groups"

    id=Column(Integer, primary_key=True, index=True)
    name=Column(String, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

    members=relationship("User", secondary=group_members, back_populates="groups")
    expenses=relationship("Expense", back_populates="group", cascade="all, delete-orphan")



class Expense(Base):
    __tablename__="expenses"

    id=Column(Integer, primary_key=True, index=True)
    group_id= Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    paid_by=Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"),nullable=False)
    amount=Column(Float, nullable=False)
    description=Column(String, nullable=False)
    created_at= Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="expenses")
    payer=relationship("User", back_populates="expenses_paid")

    