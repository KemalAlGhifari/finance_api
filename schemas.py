# schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

class ModelConfig:
    model_config = {"from_attributes": True}

class CategoryType(str, Enum):
    income = "income"
    expense = "expense"

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CategoryCreate(BaseModel):
    name: str
    type: CategoryType

class CategoryResponse(BaseModel):
    id: int
    name: str
    type: CategoryType
    created_at: datetime

    model_config = {"from_attributes": True}

class IncomeCreate(BaseModel):
    category_id: Optional[int] = None
    title: str
    amount: float
    description: Optional[str] = None
    date: date

class ExpenseCreate(BaseModel):
    category_id: Optional[int] = None
    title: str
    amount: float
    description: Optional[str] = None
    date: date

class TransactionResponse(BaseModel):
    id: int
    category_id: Optional[int]
    title: str
    amount: float
    description: Optional[str]
    date: date
    created_at: datetime

    model_config = {"from_attributes": True}

# Summary responses
class SummaryResponse(BaseModel):
    income: float
    expense: float
    balance: float
