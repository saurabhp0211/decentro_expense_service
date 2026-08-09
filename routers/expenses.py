from typing import Annotated
from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from utils import simplify_debts
from oauth2 import get_current_user


router=APIRouter()

CurrentUser= Annotated[models.User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/expenses/", response_model=schemas.ExpenseResponse, status_code=status.HTTP_201_CREATED, tags=["Expenses"])
def create_expense(expense: schemas.ExpenseCreate, db: DbSession, current_user: CurrentUser):
    if not expense.splits:
        raise HTTPException(status_code=400, detail="The 'splits' array cannot be empty.")
    if expense.amount <= 0:
        raise HTTPException(status_code=400, detail="Expense amount must be greater than 0")
    
    group = db.query(models.Group).filter(models.Group.id == expense.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group_member_ids = {member.id for member in group.members}

    # logged in user must be a member of the group
    if current_user.id not in group_member_ids:
        raise HTTPException(status_code=403, detail="You must be a member of the group to add an expense")

    # the person who supposedly paid must also be a member of the group
    if expense.payer_id not in group_member_ids:
        raise HTTPException(status_code=400, detail="The specified payer is not a member of this group")
   

    if expense.split_type == schemas.SplitType.EQUAL:
        split_count = len(expense.splits)
        owed_amount = expense.amount / split_count
        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User {split.user_id} is not in the group")
            split.amount = owed_amount

    elif expense.split_type == schemas.SplitType.EXACT:
        total_split = 0.0
        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User {split.user_id} is not in the group")
            if split.amount is None:
                raise HTTPException(status_code=400, detail="Amount is required for EXACT splits")
            total_split += split.amount
        if total_split != expense.amount:
            raise HTTPException(status_code=400, detail=f"EXACT splits sum({total_split}) must equal total amount ({expense.amount})")
        
    elif expense.split_type == schemas.SplitType.PERCENT:
        total_percent = 0.0
        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User{split.user_id} is not present in the group")
            if split.percent is None:
                raise HTTPException(status_code=400, detail="Percent is required for PERCENT splits")
            total_percent += split.percent
        if abs(total_percent- 100.0)> 0.01:
            raise HTTPException(status_code=400, detail=f"PERCENT splits must sum exactly to 100. Current sum: {total_percent}")
        
    db_expense = models.Expense(
        group_id=expense.group_id, 
        payer_id=expense.payer_id,
        created_by_id=current_user.id, 
        amount=expense.amount, 
        description=expense.description,
        split_type=expense.split_type
    )
    db.add(db_expense)
    db.flush()

    for split in expense.splits:
        owed_amount = 0.0
        if expense.split_type == schemas.SplitType.EQUAL:
            owed_amount = split.amount
        elif expense.split_type == schemas.SplitType.EXACT:
            owed_amount = split.amount
        elif expense.split_type == schemas.SplitType.PERCENT:
            owed_amount = (expense.amount * split.percent) / 100.0
        
        db_split = models.ExpenseSplit(
            expense_id=db_expense.id,
            user_id=split.user_id,
            amount_owed=round(owed_amount, 2)
        )
        db.add(db_split)

    db.commit()
    db.refresh(db_expense)
    return db_expense

@router.get("/groups/{group_id}/expenses", tags=["Expenses"])
def get_Group_Expenses(group_id: int, 
                       db:DbSession,
                       current_user: CurrentUser,
                       skip:int =Query(0, ge=0, description="Records to skip"),
                       limit: int = Query(20, le=100, description="Max records to return"),
                       ):

    group= db.query(models.Group).filter(models.Group.id== group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not authorized to view this group")
    
    expenses = (db.query(models.Expense)
               .filter(models.Expense.group_id == group_id)
               .offset(skip)
               .limit(limit)
               .all())
    return expenses


@router.get("/groups/{group_id}/balances", tags=["Balances"])
def get_group_balances(group_id: int, db: DbSession, current_user: CurrentUser):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if current_user not in group.members:
        raise HTTPException(status_code=403, detail="Not authorized to view balances")
    
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group_id).all()

    raw_transactions = []
    involved_user_ids = set()

    for expense in expenses:
        for split in expense.splits:
            if split.user_id != expense.payer_id:
                raw_transactions.append({
                    "borrower_id": split.user_id,
                    "payer_id": expense.payer_id,
                    "amount": split.amount_owed
                })
                involved_user_ids.add(split.user_id)
                involved_user_ids.add(expense.payer_id)
    
    if not involved_user_ids:
        return {"overall_balances": []}
    
    users = db.query(models.User).filter(models.User.id.in_(involved_user_ids)).all()
    user_names = {user.id: user.name for user in users}

    final_balances = simplify_debts(raw_transactions, user_names)
    return {"overall_balances": final_balances}


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Expenses"])
def delete_expense(expense_id: int, db:DbSession, current_user: CurrentUser):
    """Deletes an expense and automatically removes all associated splits."""

    expense=db.query(models.Expense).filter(models.Expense.id==expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # SECURITY 
    # Only the person who logged the expense or the person who paid it is allowed to delete it. 
    if current_user.id not in [expense.created_by_id, expense.payer_id]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this expense")

    db.delete(expense)
    db.commit()
    return 
