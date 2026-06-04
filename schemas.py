from pydantic import BaseModel,EmailStr
from typing import Optional, List
from enum import Enum

# Helps initial securing and guardrailing bad data without touching db


# user schemas 
class UserCreate(BaseModel):
    name:str
    email:EmailStr
    mobile_number:str

class UserResponse(BaseModel):
    id:int
    name:str
    email:EmailStr

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

class ExpenseResponse(BaseModel):
    id:int
    group_id:int
    payer_id:int
    amount:float
    description:str
    split_type:SplitType

    class Config:
        from_attributes=True

