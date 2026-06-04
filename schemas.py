from pydantic import BaseModel,EmailStr
from typing import Optional

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


class GroupResponse(BaseModel):
    id:int
    name:str
    description:Optional[str]=None

    class Config:
        from_attributes=True