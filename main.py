from fastapi import FastAPI, Request, status, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
        member_count=len(group.members)
        if member_count==0:
            raise HTTPException(status_code=400, detail="Cannot add expense to a group with no members")

        owed_amount= expense.amount/ member_count
        expense.splits= [
            schemas.SplitInput(user_id=member.id, amount=owed_amount)

            for member in group.members
        ]
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

@app.get("/balances/",tags=["Balances"])
def get_all_balances(db:Session=Depends(get_db)):
    expenses=db.query(models.Expense).all()

# We will track who owes whom in this dict
    debts={}

    for expense in expenses:
        payer_id= expense.payer_id

        for split in expense.splits:
            borrower_id=split.user_id

            # skipping because payer cant be borrower
            if payer_id==borrower_id:
                continue

            debt_key=(borrower_id, payer_id)

            if debt_key not in debts:
                debts[debt_key]=0.0
            debts[debt_key]+=split.amount_owed

    involved_user_ids=set()
    for borrower, payer in debts.keys():
        involved_user_ids.add(borrower)
        involved_user_ids.add(payer)
    
    users=db.query(models.User).filter(models.User.id.in_(involved_user_ids)).all()

    user_names={user.id:user.name for user in users}


    # formatting display for better coherence and readability

    final_balances=[]
    for (borrower,payer), amount in debts.items():
        if amount>0:
            borrower_name=user_names.get(borrower, f"Unknown User {borrower}")
            payer_name= user_names.get(payer, f"Unknown User {payer}")

            final_balances.append({
                "borrower_id":borrower,
                "payer_id":payer,
                "amount":round(amount,2),
                "message": f"{borrower_name} owes {payer_name} Rs{round(amount,2)}"
            })
    return {"overall_balances":final_balances}


