from pydantic import BaseModel


class UserIn(BaseModel):
    username: str
    password: str


class RecordIn(BaseModel):
    item: str
    amount: float
