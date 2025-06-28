from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Optional
from datetime import datetime
from database import get_database
from models import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse, 
    UserResponse, UserRole
)
from auth_middleware import get_current_user, get_current_manager
from bson import ObjectId

def normalize_sentiment(sentiment: str) -> str:
    """Normalize sentiment values to lowercase standard format"""
    if not sentiment:
        return "neutral"
    
    sentiment_lower = sentiment.lower()
    if sentiment_lower in ["positive", "pos"]:
        return "positive"
    elif sentiment_lower in ["negative", "neg"]:
        return "negative"
    else:
        return "neutral"

def normalize_feedback_data(feedback_dict: dict) -> dict:
    """Normalize feedback data for Pydantic model creation"""
    normalized = feedback_dict.copy()
    
    if "overall_sentiment" in normalized:
        normalized["overall_sentiment"] = normalize_sentiment(normalized["overall_sentiment"])
    
    return normalized

router = APIRouter()

@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    feedback: FeedbackCreate,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    employee = await db.users.find_one({
        "employee_id": feedback.employee_id,
        "manager_id": current_user.employee_id,
        "role": UserRole.EMPLOYEE
    })
    
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found or not in your team"
        )
    
    feedback_dict = feedback.dict()
    feedback_dict["manager_id"] = current_user.employee_id
    feedback_dict["created_at"] = datetime.utcnow()
    feedback_dict["is_acknowledged"] = False
    
    result = await db.feedback.insert_one(feedback_dict)
    created_feedback = await db.feedback.find_one({"_id": result.inserted_id})
    
    return FeedbackResponse(**normalize_feedback_data(created_feedback))

@router.get("/", response_model=List[FeedbackResponse])
async def get_feedback(
    request: Request,
    employee_id: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    query = {}
    
    if current_user.role == UserRole.MANAGER:
        query["manager_id"] = current_user.employee_id
        if employee_id:
            employee = await db.users.find_one({
                "employee_id": employee_id,
                "manager_id": current_user.employee_id
            })
            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Employee not found in your team"
                )
            query["employee_id"] = employee_id
    else:
        query["employee_id"] = current_user.employee_id
    
    feedback_list = await db.feedback.find(query).sort("created_at", -1).to_list(None)
    return [FeedbackResponse(**normalize_feedback_data(feedback)) for feedback in feedback_list]

@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(
    feedback_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback ID"
        )
    
    feedback = await db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    

    if current_user.role == UserRole.MANAGER:
        if feedback["manager_id"] != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view feedback you've given"
            )
    else:
        if feedback["employee_id"] != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own feedback"
            )
    
    return FeedbackResponse(**normalize_feedback_data(feedback))

@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: str,
    feedback_update: FeedbackUpdate,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback ID"
        )
    
    existing_feedback = await db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    if existing_feedback["manager_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update feedback you've given"
        )
    
    update_data = {k: v for k, v in feedback_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.feedback.update_one(
        {"_id": ObjectId(feedback_id)},
        {"$set": update_data}
    )
    
    updated_feedback = await db.feedback.find_one({"_id": ObjectId(feedback_id)})
    return FeedbackResponse(**normalize_feedback_data(updated_feedback))

@router.post("/{feedback_id}/acknowledge")
async def acknowledge_feedback(
    feedback_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employees can acknowledge feedback"
        )
    
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback ID"
        )
    
    feedback = await db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    if feedback["employee_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only acknowledge your own feedback"
        )
    
    await db.feedback.update_one(
        {"_id": ObjectId(feedback_id)},
        {
            "$set": {
                "is_acknowledged": True,
                "acknowledged_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Feedback acknowledged successfully"}

@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    if not ObjectId.is_valid(feedback_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid feedback ID"
        )
    
    feedback = await db.feedback.find_one({"_id": ObjectId(feedback_id)})
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found"
        )
    
    if feedback["manager_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete feedback you've given"
        )
    
    await db.feedback.delete_one({"_id": ObjectId(feedback_id)})
    return {"message": "Feedback deleted successfully"}
