from pydantic import BaseModel,EmailStr
from typing import Optional, List
from enum import Enum
from datetime import datetime

# Helps initial securing and guardrailing bad data without touching db


# user schemas 
class UserCreate(BaseModel):
    name:str
    email:EmailStr
    mobile_number:str
    password:str

class UserResponse(BaseModel):
    id:int
    name:str
    email:EmailStr
    created_at: datetime

    class Config:
        from_attributes=True
    


# group schemas 
class GroupCreate(BaseModel):
    name:str
    description:Optional[str]=None

class GroupMemberAdd(BaseModel):
    user_id: int


class GroupResponse(BaseModel):
    id:int
    name:str
    description:Optional[str]=None

    class Config:
        from_attributes=True


# expense scehmas --
class SplitType(str, Enum):
    EQUAL="EQUAL"
    EXACT="EXACT"
    PERCENT="PERCENT"

class SplitInput(BaseModel):
    user_id:int
    amount:Optional[float]=None
    percent: Optional[float]=None


class ExpenseCreate(BaseModel):
    group_id:int
    payer_id:int
    amount:float
    description:str
    split_type:SplitType
    splits: List[SplitInput]

class ExpenseSplitResponse(BaseModel):
    user_id:int
    amount_owed:float

    class Config:
        from_attributes=True

class ExpenseResponse(BaseModel):
    id:int
    group_id:int
    payer_id: int
    created_by_id: int
    amount:float
    description:str
    split_type:SplitType
    created_at:datetime

    splits: List[ExpenseSplitResponse]=[]

    class Config:
        from_attributes=True




class UserListResponse(BaseModel):
    data: List[UserResponse]
    

class GroupListresponse(BaseModel):
    data: List[GroupResponse]