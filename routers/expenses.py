from typing import Annotated, List
from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from utils import simplify_debts, fetch_and_calculate_balances
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
        base_amount=round(expense.amount/split_count,2)

        # calculating exactly how much is missing due to rounding
        total_base=base_amount*split_count
        remainder=round(expense.amount-total_base,2)

        for i, split in enumerate(expense.splits):
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User {split.user_id} is not in the group")

            split.amount=base_amount

            if i==0:
                split.amount+=remainder
        

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


@router.post("/groups/{group_id}/settlements", status_code=status.HTTP_201_CREATED,tags=["Expenses"])
def create_settlement(
    group_id: int,
    settlement: schemas.SettlementCreate,
    db:DbSession,
    current_user: CurrentUser
):
    payer_id= current_user.id

    # prevents settling with yourself
    if payer_id==settlement.receiver_id:
        raise HTTPException(status_code=400, detail="You cannot settle a debt with yourself")
    

    # validation-- Ensures receiver exists in the group
    group=db.query(models.Group).filter(models.Group.id==group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    receiver_in_group=any(member.id==settlement.receiver_id for member in group.members)
    if not receiver_in_group:
        raise HTTPException(status_code=400, detail="Receiver is not a member of this group.") 


    # new validation layer for the owed amount
    current_balances=fetch_and_calculate_balances(group_id, db)

    current_debt=0.0
    for debt in current_balances:
        if debt["borrower_id"]==payer_id and debt["payer_id"] == settlement.receiver_id:
            current_debt=debt["amount"]
            break

    if current_debt<=0:
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction: You do not currently owe this user any money."
        )

    if settlement.amount>current_debt:
        raise HTTPException(status_code=400,
                            detail=f"Overpayment blocked: You only owe Rs{current_debt}. Please adjust the settlement amount." 
                            )



    db_settlement=models.Expense(
        group_id=group_id,
        created_by_id=payer_id,
        payer_id=payer_id,
        amount=settlement.amount,
        description="Debt Settlement",
        split_type= schemas.SplitType.SETTLEMENT
    )

    db.add(db_settlement)
    db.flush()

    db_split=models.ExpenseSplit(
        expense_id=db_settlement.id,
        user_id=settlement.receiver_id,
        amount_owed=settlement.amount
    )

    db.add(db_split)
    db.commit()
    db.refresh(db_settlement)

    return {"message": "Settlement processed successfully", "settlement_id": db_settlement.id}

@router.get("/groups/{group_id}/expenses", response_model=List[schemas.ExpenseResponse], tags=["Expenses"])
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
    
    
    final_balances = fetch_and_calculate_balances(group_id, db)

    return {"overall_balances": final_balances}


@router.delete("/groups/{group_id}/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Expenses"])
def delete_expense(group_id:int, expense_id: int, db:DbSession, current_user: CurrentUser):
    """Deletes an expense and automatically removes all associated splits."""

    expense=db.query(models.Expense).filter(models.Expense.id==expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.group_id!=group_id:
        raise HTTPException(status_code=404, detail="Expense not found in this group")
    
    # SECURITY 
    # Only the person who logged the expense or the person who paid it is allowed to delete it. 
    if current_user.id not in [expense.created_by_id, expense.payer_id]:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this expense")

    db.delete(expense)
    db.commit()
    return 
