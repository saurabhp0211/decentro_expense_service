from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router= APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db:Session = Depends(get_db)):
    """This will create a new user in the database."""
    db_user = models.User(name=user.name, email=user.email, mobile_number=user.mobile_number)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=schemas.UserListResponse)
def get_users(db:Session = Depends(get_db)):
    users = db.query(models.User).all()
    return {"data": users}

