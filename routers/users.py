from fastapi import APIRouter, status, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from oauth2 import hash_password, get_current_user
from typing import Annotated

router= APIRouter(
    prefix="/users",
    tags=["Users"]
)

Current_User=Annotated[models.User, Depends(get_current_user)]


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

@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: Current_User):
    """Returns the profile of the currently authenticated user.
       No database session required here because the authentication dependency already fetched the user. """

    return current_user

