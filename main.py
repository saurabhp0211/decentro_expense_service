from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from utils import simplify_debts

import models
import schemas
from database import SessionLocal, engine


models.Base.metadata.create_all(bind=engine)

# to initialize the application
app=FastAPI(title="Decentro Expense Sharing API")

# database session dependency
def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()


#global handler for database conflicts
@app.exception_handler(IntegrityError)
async def sqlalchemy_integrity_error_handler(request:Request, exc:IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Database Conflict",
            "message": "This record already exists. For example, this email might already be registered"
        }
    )


@app.get("/")
def health_check():
    return {"status": "Decentro Expense Engine Active"}

# user endpoints -->

@app.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED,tags=["Users"])
def create_user(user:schemas.UserCreate, db:Session=Depends(get_db)):
    """This will create a new user in the database."""
    db_user=models.User(name=user.name, email=user.email, mobile_number=user.mobile_number)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# list all users
@app.get("/users/", response_model=schemas.UserListResponse, tags=["Users"])
def get_users(db: Session = Depends(get_db)):
    users=db.query(models.User).all()
    return {"data":users}



# group endpoints --->
@app.post("/groups/", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED, tags=["Groups"])
def create_group(group: schemas.GroupCreate, db:Session=Depends(get_db)):
    """Creates a new expense sharing group"""
    db_group=models.Group(name=group.name, description=group.description)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@app.post("/groups/{group_id}/members",tags=["Groups"])
def add_user_To_group(group_id: int, member: schemas.GroupMemberAdd, db: Session = Depends(get_db)):
    """Adds a user to an existing group"""

    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
        
    user = db.query(models.User).filter(models.User.id == member.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user in group.members:
        raise HTTPException(status_code=400, detail="User is already in this group")
    
    
    group.members.append(user)
    db.commit()
    return {"message": f"User '{user.name}' successfully added to group '{group.name}'"}


@app.get("/groups/{group_id}/members",tags=["Groups"])
def get_group_Members(group_id: int, db: Session = Depends(get_db)):
    """Returns all members belonging to a group"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.members


@app.get("/groups/", response_model=schemas.GroupListresponse,tags=["Groups"])
def get_groups(db:Session=Depends(get_db)):
    groups=db.query(models.Group).all()
    return {"data":groups}



# expense endpoints --
@app.post("/expenses/", response_model=schemas.ExpenseResponse, status_code=status.HTTP_201_CREATED,tags=["Expenses"])
def create_expense(expense:schemas.ExpenseCreate, db:Session=Depends(get_db)):

    # logic for validation 

    if not expense.splits:
        raise HTTPException(status_code=400, detail="The 'splits' array cannot be empty.")

    if expense.amount <= 0:
        raise HTTPException(status_code=400, detail="Expense amount must be greater than 0")
    
    group=db.query(models.Group).filter(models.Group.id==expense.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # verifying if all users belong to the group ---
    group_member_ids= {member.id for member in group.members}

    if expense.payer_id not in group_member_ids:
        raise HTTPException(status_code=400, detail="The payer must be a member of the group")


    if expense.split_type==schemas.SplitType.EQUAL:
        split_count=len(expense.splits)
        owed_amount=expense.amount/split_count
        
        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User {split.user_id} is not in the group")
            
            split.amount= owed_amount
# validation of exact splits ------
    elif expense.split_type==schemas.SplitType.EXACT:
        total_split=0.0
        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User {split.user_id} is not in the group")
            
            if split.amount is None:
                raise HTTPException(status_code=400, detail="Amount is required for EXACT splits")
            
            total_split+=split.amount

        if total_split!=expense.amount:
            raise HTTPException(status_code=400, detail=f"EXACT splits sum({total_split}) must equal total amount ({expense.amount})")
        

        # validating percent splits
    elif expense.split_type==schemas.SplitType.PERCENT:
        total_percent=0.0

        for split in expense.splits:
            if split.user_id not in group_member_ids:
                raise HTTPException(status_code=400, detail=f"User{split.user_id} is not present in the group")
            
            if split.percent is None:
                raise HTTPException(status_code=400, detail="Percent is required for PERCENT splits")

            total_percent+=split.percent

        if total_percent !=100.0:
            raise HTTPException(status_code=400, detail=f"PERCENT splits must sum exactly to 100. Current sum: {total_percent}")
        


    db_expense=models.Expense(
        group_id=expense.group_id, 
        payer_id=expense.payer_id,
        amount=expense.amount, 
        description=expense.description,
        split_type=expense.split_type
    )
    db.add(db_expense)
    db.flush()


    for split in expense.splits:
        owed_amount=0.0

        if expense.split_type== schemas.SplitType.EQUAL:
            owed_amount= split.amount

        elif expense.split_type==schemas.SplitType.EXACT:
            owed_amount=split.amount
        elif expense.split_type==schemas.SplitType.PERCENT:
            owed_amount=(expense.amount* split.percent)/100.0
        
        db_split=models.ExpenseSplit(
            expense_id=db_expense.id,
            user_id=split.user_id,
            amount_owed=round(owed_amount,2)
        )
        db.add(db_split)

    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/groups/{group_id}/expenses",tags=["Expenses"])
def get_Group_Expenses(group_id: int, db: Session = Depends(get_db)):
    expenses = db.query(models.Expense).filter(models.Expense.group_id == group_id).all()
    return expenses


# balances endpoint

@app.get("/groups/{group_id}/balances", tags=["Balances"])
def get_group_balances(group_id:int, db:Session=Depends(get_db)):

    group=db.query(models.Group).filter(models.Group.id==group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    expenses=db.query(models.Expense).filter(models.Expense.group_id==group_id).all()

    raw_transactions=[]
    involved_user_ids=set()

    for expense in expenses:
        for split in expense.splits:
            if split.user_id !=expense.payer_id:
                raw_transactions.append({
                    "borrower_id":split.user_id,
                    "payer_id":expense.payer_id,
                    "amount":split.amount_owed
                })
                involved_user_ids.add(split.user_id)
                involved_user_ids.add(expense.payer_id)
    

    # We only fetch users who are actually involved in debts in this group
    if not involved_user_ids:
        return {"overall_balances": []}
    
    users=db.query(models.User).filter(models.User.id.in_(involved_user_ids)).all()
    user_names= {user.id: user.name for user in users}

    # passing through the simplification algo
    final_balances=simplify_debts(raw_transactions,user_names)

    return {"overall_balances": final_balances}

