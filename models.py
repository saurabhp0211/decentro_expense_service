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
    mobile_number=Column(String, unique=True, index=True, nullable=False)
    created_at=Column(DateTime(timezone=True), server_default=func.now())
    password=Column(String)

    groups=relationship("Group",secondary=group_members, back_populates="members")  
    expenses_paid= relationship("Expense", foreign_keys="Expense.payer_id",back_populates="payer")     #one to many

    expenses_created=relationship("Expense", foreign_keys="Expense.created_by_id", back_populates="creator")

class Group(Base):
    __tablename__="groups"

    id=Column(Integer, primary_key=True, index=True)
    name=Column(String, nullable=False)
    description=Column(String,nullable=True)
    created_at=Column(DateTime(timezone=True), server_default=func.now())

    members=relationship("User", secondary=group_members, back_populates="groups")
    expenses=relationship("Expense", back_populates="group", cascade="all, delete-orphan")



class Expense(Base):
    __tablename__="expenses"

    id=Column(Integer, primary_key=True, index=True)
    group_id= Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    payer_id=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),nullable=False)

    created_by_id= Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount=Column(Float, nullable=False)
    description=Column(String, nullable=False)
    split_type=Column(String, nullable=False)
    created_at= Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="expenses")
    payer=relationship("User", foreign_keys=[payer_id],back_populates="expenses_paid")

    
    # Relationship for audit trail
    creator=relationship("User", foreign_keys=[created_by_id])
    splits=relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


class ExpenseSplit(Base):
    __tablename__="expense_splits"

    id=Column(Integer, primary_key=True, index=True)
    expense_id=Column(Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False)
    user_id=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount_owed=Column(Float, nullable=False)

    expense=relationship("Expense", back_populates="splits")

    