from oauth2 import verify_password, create_access_token
from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
import models
from database import get_db
from fastapi.security import OAuth2PasswordRequestForm

router=APIRouter(tags=["Authentication"])

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm= Depends(), db:Session=Depends(get_db)):
   
    user=db.query(models.User).filter(models.User.email == form_data.username).first()

    

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate":"Bearer"}
        )
    access_token= create_access_token(data={"user_id":user.id})

    return {"access_token": access_token, "token_type": "bearer"}