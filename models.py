from pydantic import BaseModel, EmailStr, Field, ConfigDict, root_validator
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum
from bson import ObjectId
from pydantic_core import core_schema

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler
    ) -> core_schema.CoreSchema:
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

class UserRole(str, Enum):
    MANAGER = "manager"
    EMPLOYEE = "employee"

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class FormFieldType(str, Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    DATETIMELOCAL = 'datetime-local'
    DATE = 'date'
    TIME = 'time'
    NUMBER = 'number'
    EMAIL = 'email'
    PASSWORD = 'password'

# User Models
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    employee_id: str
    department: Optional[str] = None
    manager_id: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Annotated[PyObjectId, Field(alias="_id")] = Field(default_factory=PyObjectId)
    created_at: datetime
    is_active: bool = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Feedback Models
class FeedbackBase(BaseModel):
    employee_id: str
    strengths: str
    areas_to_improve: str
    overall_sentiment: SentimentType
    additional_notes: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None 
    form_id: Optional[str] = None 

class FeedbackCreate(FeedbackBase):
    pass

class FeedbackUpdate(BaseModel):
    strengths: Optional[str] = None
    areas_to_improve: Optional[str] = None
    overall_sentiment: Optional[SentimentType] = None
    additional_notes: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None

class FeedbackResponse(FeedbackBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Annotated[PyObjectId, Field(alias="_id")] = Field(default_factory=PyObjectId)
    manager_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

# Form Models
class FormField(BaseModel):
    id: Optional[str]
    label: str
    type: FormFieldType
    required: bool = False
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None
    name: Optional[str] = None  # New field

    @root_validator(pre=True)
    def auto_generate_id_and_name(cls, values):
        label = values.get("label", "")
        if label:
            if not values.get("id"):
                values["id"] = label.lower().replace(" ", "_")
            if not values.get("name"):
                values["name"] = cls.to_camel_case(label)
        return values

    @staticmethod
    def to_camel_case(label: str) -> str:
        words = label.strip().split()
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

class FeedbackFormBase(BaseModel):
    title: str
    description: Optional[str] = None
    fields: List[FormField]
    is_active: bool = True

class FeedbackFormCreate(FeedbackFormBase):
    pass

class FeedbackFormUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[List[FormField]] = None
    is_active: Optional[bool] = None

class FeedbackFormResponse(FeedbackFormBase):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )
    
    id: Annotated[PyObjectId, Field(alias="_id")] = Field(default_factory=PyObjectId)
    manager_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    submission_count: Optional[int] = None  

# New models for form submissions
class FormSubmissionRequest(BaseModel):
    """Request model for submitting a form"""
    form_data: Dict[str, Any]
    target_employee_id: Optional[str] = None 

class FormSubmissionStats(BaseModel):
    """Statistics for form submissions"""
    form_id: str
    form_title: str
    total_submissions: int
    submissions_by_employee: Dict[str, int]
    latest_submission: Optional[datetime] = None

# Dashboard Models
class TeamMemberStats(BaseModel):
    employee_id: str
    full_name: str
    feedback_count: int
    latest_feedback_date: Optional[datetime] = None
    sentiment_distribution: Dict[str, int]

class ManagerDashboard(BaseModel):
    team_size: int
    total_feedback_given: int
    team_members: List[TeamMemberStats]
    sentiment_trends: Dict[str, int]
    active_forms_count: Optional[int] = 0
    form_submissions_count: Optional[int] = 0

class EmployeeDashboard(BaseModel):
    total_feedback_received: int
    unacknowledged_count: int
    recent_feedback: List[FeedbackResponse]
    sentiment_distribution: Dict[str, int]
    available_forms_count: Optional[int] = 0

# Token Models
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ManagerResponse(BaseModel):
    label: str
    value: str