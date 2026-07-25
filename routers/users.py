from fastapi import APIRouter, status, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from oauth2 import hash_password

router= APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db:Session = Depends(get_db)):
    """This will create a new user in the database."""

    existing_user=db.query(models.User).filter(models.User.email==user.email).first()

    if existing_user:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    hashed_pwd=hash_password(user.password)

    db_user = models.User(name=user.name, 
                          email=user.email,
                            mobile_number=user.mobile_number,
                            password=hashed_pwd
                        )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=schemas.UserListResponse)
def get_users(
    skip: int= Query(0, ge=0, description="Records to skip"),
    limit: int= Query(20, le=100, description="Max records to return"),
    db:Session = Depends(get_db)):


    users = db.query(models.User).offset(skip).limit(limit).all()
    return {"data": users}

