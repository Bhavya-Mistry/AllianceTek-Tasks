from pydantic import BaseModel

class StudentCreate(BaseModel):
    name:str
    email:str
    age:int

class StudentUpdate(BaseModel):
    name:str
    email:str
    age:int

class StudentRead(BaseModel):
    name:str
    email:str
    age:int
