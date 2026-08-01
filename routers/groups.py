from fastapi import APIRouter, status, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db
from oauth2 import get_current_user


router=APIRouter(
    prefix="/groups",
    tags=["Groups"]
)

@router.post("/", response_model=schemas.GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate, 
                 db:Session=Depends(get_db),
                 current_user: models.User= Depends(get_current_user)):
    """Creates a new expense sharing group"""
    db_group = models.Group(name=group.name, description=group.description)
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


@router.post("/{group_id}/members")
def add_user_To_group(group_id: int, member: schemas.GroupMemberAdd, db:Session=Depends(get_db)):
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


@router.get("/{group_id}/members")
def get_group_members(group_id:int, db:Session=Depends(get_db)):
    """Returns all members belonging to a group"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group.members


@router.get("/", response_model=schemas.GroupListresponse)
def get_groups(
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int =Query(20, le=100, description="Max records to return"),
    db: Session = Depends(get_db)):

    groups = db.query(models.Group).offset(skip).limit(limit).all()
    return {"data": groups}