from pydantic import BaseModel

class UserCreate(BaseModel):
    name:str
    age:int
    email:str

class UserRead(BaseModel):
    name:str
    age:int