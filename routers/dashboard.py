from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict
from database import get_database
from models import (
    UserResponse, UserRole, ManagerDashboard, EmployeeDashboard,
    TeamMemberStats, FeedbackResponse
)
from auth_middleware import get_current_user
from datetime import datetime, timedelta

router = APIRouter()

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

@router.get("/manager", response_model=ManagerDashboard)
async def get_manager_dashboard(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can access this dashboard"
        )
    
    team_members = await db.users.find({
        "manager_id": current_user.employee_id,
        "role": UserRole.EMPLOYEE,
        "is_active": True
    }).to_list(None)
    
    all_feedback = await db.feedback.find({
        "manager_id": current_user.employee_id
    }).to_list(None)
    
    team_stats = []
    sentiment_trends = {"positive": 0, "neutral": 0, "negative": 0}
    
    for member in team_members:
        member_feedback = [f for f in all_feedback if f["employee_id"] == member["employee_id"]]
        
        sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
        latest_date = None
        
        for feedback in member_feedback:
            sentiment = normalize_sentiment(feedback.get("overall_sentiment", "neutral"))
            sentiment_dist[sentiment] += 1
            sentiment_trends[sentiment] += 1
            
            if not latest_date or feedback["created_at"] > latest_date:
                latest_date = feedback["created_at"]
        
        team_stats.append(TeamMemberStats(
            employee_id=member["employee_id"],
            full_name=member["full_name"],
            feedback_count=len(member_feedback),
            latest_feedback_date=latest_date,
            sentiment_distribution=sentiment_dist
        ))
    
    active_forms_count = await db.forms.count_documents({
        "manager_id": current_user.employee_id,
        "is_active": True
    })

    form_submissions_count = await db.feedback.count_documents({
        "manager_id": current_user.employee_id,
        "form_id": {"$exists": True}
    })
    
    return ManagerDashboard(
        team_size=len(team_members),
        total_feedback_given=len(all_feedback),
        team_members=team_stats,
        sentiment_trends=sentiment_trends,
        active_forms_count=active_forms_count,
        form_submissions_count=form_submissions_count
    )

@router.get("/employee", response_model=EmployeeDashboard)
async def get_employee_dashboard(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    if current_user.role != UserRole.EMPLOYEE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only employees can access this dashboard"
        )
    
    all_feedback = await db.feedback.find({
        "employee_id": current_user.employee_id
    }).sort("created_at", -1).to_list(None)
    
    unacknowledged_count = len([f for f in all_feedback if not f.get("is_acknowledged", False)])

    sentiment_distribution = {"positive": 0, "neutral": 0, "negative": 0}
    for feedback in all_feedback:
        sentiment = normalize_sentiment(feedback.get("overall_sentiment", "neutral"))
        sentiment_distribution[sentiment] += 1
    
    available_forms_count = 0
    if current_user.manager_id:
        available_forms_count = await db.forms.count_documents({
            "manager_id": current_user.manager_id,
            "is_active": True
        })
    
    recent_feedback = []
    for feedback_dict in all_feedback[:5]:
        normalized_feedback = normalize_feedback_data(feedback_dict)
        recent_feedback.append(FeedbackResponse(**normalized_feedback))
    
    return EmployeeDashboard(
        total_feedback_received=len(all_feedback),
        unacknowledged_count=unacknowledged_count,
        recent_feedback=recent_feedback,
        sentiment_distribution=sentiment_distribution,
        available_forms_count=available_forms_count
    )

@router.get("/stats")
async def get_dashboard_stats(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get general stats for the current user"""
    if current_user.role == UserRole.MANAGER:
        team_count = await db.users.count_documents({
            "manager_id": current_user.employee_id,
            "role": UserRole.EMPLOYEE,
            "is_active": True
        })
        
        feedback_count = await db.feedback.count_documents({
            "manager_id": current_user.employee_id
        })
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_feedback_count = await db.feedback.count_documents({
            "manager_id": current_user.employee_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        return {
            "role": "manager",
            "team_size": team_count,
            "total_feedback_given": feedback_count,
            "recent_feedback_count": recent_feedback_count
        }
    
    else:
        total_feedback = await db.feedback.count_documents({
            "employee_id": current_user.employee_id
        })
        
        unacknowledged = await db.feedback.count_documents({
            "employee_id": current_user.employee_id,
            "is_acknowledged": False
        })
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_feedback_count = await db.feedback.count_documents({
            "employee_id": current_user.employee_id,
            "created_at": {"$gte": thirty_days_ago}
        })
        
        return {
            "role": "employee",
            "total_feedback_received": total_feedback,
            "unacknowledged_count": unacknowledged,
            "recent_feedback_count": recent_feedback_count
        }
