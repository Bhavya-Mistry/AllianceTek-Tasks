from pydantic import BaseModel, EmailStr

class StudentCreate(BaseModel):
    name:str
    email:EmailStr
    age:int

class StudentUpdate(BaseModel):
    name:str
    email:EmailStr
    age:int

class StudentRead(BaseModel):
    name:str
    email:EmailStr
    age:int
