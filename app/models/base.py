from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

class PaymentFrequency(str, Enum):
    monthly = "monthly"
    bimonthly = "bimonthly"
    quarterly = "quarterly"

class PaymentType(str, Enum):
    credit = "credit"
    debit = "debit"

class PaymentStatus(str, Enum):
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"

class SourceType(str, Enum):
    vehicle = "vehicle"
    outside_interest = "outside_interest"
    loan = "loan"
    other = "other"

# Authentication Models
class LoginRequest(BaseModel):
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# Vehicle Models
class VehicleBase(BaseModel):
    vehicle_name: str = Field(..., min_length=1, max_length=100)
    principle_amount: float = Field(..., gt=0, le=99999999.99)
    rent: float = Field(..., gt=0, le=99999999.99)
    payment_frequency: PaymentFrequency
    date_of_lending: date
    lend_to: str = Field(..., min_length=1, max_length=100)

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    vehicle_name: Optional[str] = Field(None, min_length=1, max_length=100)
    principle_amount: Optional[float] = Field(None, gt=0, le=99999999.99)
    rent: Optional[float] = Field(None, gt=0, le=99999999.99)
    payment_frequency: Optional[PaymentFrequency] = None
    date_of_lending: Optional[date] = None
    lend_to: Optional[str] = Field(None, min_length=1, max_length=100)

class VehicleResponse(VehicleBase):
    id: int
    is_closed: bool
    closure_date: Optional[date] = None
    created_at: datetime
    extended_days: Optional[int] = None
    total_payments: float = 0.0
    pending_amount: float = 0.0

# Outside Interest Models
class OutsideInterestBase(BaseModel):
    to_whom: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    principle_amount: float = Field(..., gt=0)
    interest_rate_percentage: float = Field(..., gt=0, le=100, description="Interest rate as percentage per annum")
    interest_rate_indian: float = Field(..., gt=0, le=100, description="Indian interest rate (1 rupee = 12% annually)")
    payment_frequency: PaymentFrequency
    date_of_lending: date
    lend_to: str = Field(..., min_length=1, max_length=100)
    
    @field_validator('interest_rate_percentage', 'interest_rate_indian')
    @classmethod
    def validate_interest_rates(cls, v, info):
        # Both interest rates are required and must be consistent
        if info.field_name == 'interest_rate_percentage':
            # Get the other field value from the model data
            model_data = info.data
            indian_rate = model_data.get('interest_rate_indian')
            if indian_rate and abs(v - (indian_rate * 12)) > 0.01:
                raise ValueError('Interest rates are not consistent. Percentage should be Indian rate × 12')
        elif info.field_name == 'interest_rate_indian':
            model_data = info.data
            percentage_rate = model_data.get('interest_rate_percentage')
            if percentage_rate and abs(percentage_rate - (v * 12)) > 0.01:
                raise ValueError('Interest rates are not consistent. Indian rate should be Percentage ÷ 12')
        return v

class OutsideInterestCreate(OutsideInterestBase):
    pass

class OutsideInterestUpdate(BaseModel):
    to_whom: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    principle_amount: Optional[float] = Field(None, gt=0)
    interest_rate_percentage: Optional[float] = Field(None, gt=0, le=100, description="Interest rate as percentage per annum")
    interest_rate_indian: Optional[float] = Field(None, gt=0, le=100, description="Indian interest rate (1 rupee = 12% annually)")
    payment_frequency: Optional[PaymentFrequency] = None
    date_of_lending: Optional[date] = None
    lend_to: Optional[str] = Field(None, min_length=1, max_length=100)
    
    @field_validator('interest_rate_percentage', 'interest_rate_indian')
    @classmethod
    def validate_interest_rates(cls, v, info):
        # Both interest rates are required and must be consistent
        if info.field_name == 'interest_rate_percentage':
            # Get the other field value from the model data
            model_data = info.data
            indian_rate = model_data.get('interest_rate_indian')
            if indian_rate and abs(v - (indian_rate * 12)) > 0.01:
                raise ValueError('Interest rates are not consistent. Percentage should be Indian rate × 12')
        elif info.field_name == 'interest_rate_indian':
            model_data = info.data
            percentage_rate = model_data.get('interest_rate_percentage')
            if percentage_rate and abs(percentage_rate - (v * 12)) > 0.01:
                raise ValueError('Interest rates are not consistent. Indian rate should be Percentage ÷ 12')
        return v

class OutsideInterestResponse(OutsideInterestBase):
    id: int
    is_closed: bool
    closure_date: Optional[date] = None
    created_at: datetime
    extended_days: Optional[int] = None
    total_payments: float = 0.0
    pending_amount: float = 0.0

# Loan Models
class LoanBase(BaseModel):
    lender_name: str = Field(..., min_length=1, max_length=100)
    lender_type: str = Field(..., min_length=1, max_length=100)
    principle_amount: float = Field(..., gt=0)
    interest_rate: float = Field(..., gt=0, le=100)
    interest_rate_indian: float = Field(..., gt=0, le=100)
    payment_frequency: PaymentFrequency
    date_of_borrowing: date

class LoanCreate(LoanBase):
    pass

class LoanUpdate(BaseModel):
    lender_name: Optional[str] = Field(None, min_length=1, max_length=100)
    lender_type: Optional[str] = Field(None, min_length=1, max_length=100)
    principle_amount: Optional[float] = Field(None, gt=0)
    interest_rate: Optional[float] = Field(None, gt=0, le=100)
    interest_rate_indian: Optional[float] = Field(None, gt=0, le=100)
    payment_frequency: Optional[PaymentFrequency] = None
    date_of_borrowing: Optional[date] = None

class LoanResponse(LoanBase):
    id: int
    is_closed: bool
    closure_date: Optional[date] = None
    created_at: datetime
    extended_days: Optional[int] = None
    total_payments: float = 0.0
    pending_amount: float = 0.0

# Payment Models
class PaymentBase(BaseModel):
    source_type: SourceType
    source_id: Optional[int] = None
    payment_type: PaymentType
    payment_date: date
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    payment_status: PaymentStatus

class PaymentCreate(PaymentBase):
    pass

# Simple payment model for vehicle payments
class VehiclePaymentCreate(BaseModel):
    vehicle_id: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    payment_date: date
    notes: Optional[str] = None

class PaymentUpdate(BaseModel):
    source_type: Optional[SourceType] = None
    source_id: Optional[int] = None
    payment_type: Optional[PaymentType] = None
    payment_date: Optional[date] = None
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None

class PaymentResponse(PaymentBase):
    id: int
    created_at: datetime

# Dashboard Models
class DashboardSummary(BaseModel):
    total_vehicles: int
    active_vehicles: int
    closed_vehicles: int
    total_outside_interest: int
    active_outside_interest: int
    closed_outside_interest: int
    total_loans: int
    active_loans: int
    closed_loans: int
    total_payments_this_month: float
    pending_payments: float
    total_principle_amount: float

class FinanceOverview(BaseModel):
    vehicles: List[VehicleResponse]
    outside_interests: List[OutsideInterestResponse]
    loans: List[LoanResponse]
    recent_payments: List[PaymentResponse]
    summary: DashboardSummary
