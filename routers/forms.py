from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Dict, Any
from datetime import datetime
from database import get_database
from models import (
    FeedbackFormCreate, FeedbackFormUpdate, FeedbackFormResponse,
    UserResponse, UserRole, FeedbackCreate, FeedbackResponse
)
from auth_middleware import get_current_manager, get_current_user
from bson import ObjectId

router = APIRouter()

@router.post("/", response_model=FeedbackFormResponse)
async def create_feedback_form(
    form: FeedbackFormCreate,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    """Create a custom feedback form template"""
    form_dict = form.dict()
    form_dict["manager_id"] = current_user.employee_id
    form_dict["created_at"] = datetime.utcnow()
    
    result = await db.forms.insert_one(form_dict)
    created_form = await db.forms.find_one({"_id": result.inserted_id})
    
    return FeedbackFormResponse(**created_form)

@router.get("/", response_model=List[FeedbackFormResponse])
async def get_feedback_forms(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all feedback forms - managers see their forms, employees see their manager's forms"""
    if current_user.role == UserRole.MANAGER:
        forms = await db.forms.find({
            "manager_id": current_user.employee_id
        }).sort("created_at", -1).to_list(None)
    else:
        if not current_user.manager_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee has no assigned manager"
            )
        
        forms = await db.forms.find({
            "manager_id": current_user.manager_id,
            "is_active": True
        }).sort("created_at", -1).to_list(None)
    
    forms_with_submissions = []
    for form in forms:
        form_id = str(form["_id"])
        
        submission_count = await db.feedback.count_documents({
            "form_id": form_id
        })
        
        form_with_count = form.copy()
        form_with_count["submission_count"] = submission_count
        
        forms_with_submissions.append(FeedbackFormResponse(**form_with_count))
    
    return forms_with_submissions


@router.get("/{form_id}", response_model=FeedbackFormResponse)
async def get_feedback_form(
    form_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get a specific feedback form"""
    if not ObjectId.is_valid(form_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form ID"
        )
    
    form = await db.forms.find_one({"_id": ObjectId(form_id)})
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )
    
    if current_user.role == UserRole.MANAGER:
        if form["manager_id"] != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view forms you've created"
            )
    else:
        if form["manager_id"] != current_user.manager_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view forms created by your manager"
            )
        
        if not form.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Form not found or not active"
            )
    
    return FeedbackFormResponse(**form)

@router.put("/{form_id}", response_model=FeedbackFormResponse)
async def update_feedback_form(
    form_id: str,
    form_update: FeedbackFormUpdate,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    """Update a feedback form"""
    if not ObjectId.is_valid(form_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form ID"
        )
    
    existing_form = await db.forms.find_one({"_id": ObjectId(form_id)})
    if not existing_form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )

    if existing_form["manager_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update forms you've created"
        )
    
    update_data = {k: v for k, v in form_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.forms.update_one(
        {"_id": ObjectId(form_id)},
        {"$set": update_data}
    )
    
    updated_form = await db.forms.find_one({"_id": ObjectId(form_id)})
    return FeedbackFormResponse(**updated_form)

@router.delete("/{form_id}")
async def delete_feedback_form(
    form_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    """Delete a feedback form"""
    if not ObjectId.is_valid(form_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form ID"
        )
    
    form = await db.forms.find_one({"_id": ObjectId(form_id)})
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )
    
    if form["manager_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete forms you've created"
        )
    
    await db.forms.delete_one({"_id": ObjectId(form_id)})
    return {"message": "Form deleted successfully"}

@router.get("/active/list", response_model=List[FeedbackFormResponse])
async def get_active_forms(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all active feedback forms"""
    if current_user.role == UserRole.MANAGER:
        forms = await db.forms.find({
            "manager_id": current_user.employee_id,
            "is_active": True
        }).sort("created_at", -1).to_list(None)
    else:
        if not current_user.manager_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee has no assigned manager"
            )
        
        forms = await db.forms.find({
            "manager_id": current_user.manager_id,
            "is_active": True
        }).sort("created_at", -1).to_list(None)
    
    return [FeedbackFormResponse(**form) for form in forms]

@router.post("/{form_id}/submit", response_model=FeedbackResponse)
async def submit_feedback_form(
    form_id: str,
    form_data: Dict[str, Any],
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    """Submit feedback using a specific form (employees can submit, managers can submit for their team members)"""
    if not ObjectId.is_valid(form_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form ID"
        )
    
    form = await db.forms.find_one({"_id": ObjectId(form_id)})
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )
    
    if not form.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Form is not active"
        )
    
    if current_user.role == UserRole.EMPLOYEE:
        if form["manager_id"] != current_user.manager_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only use forms created by your manager"
            )
        
        employee_id = current_user.employee_id
        manager_id = current_user.manager_id
        
    else:  # Manager
        if form["manager_id"] != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only use forms you've created"
            )
        
        target_employee_id = form_data.get("target_employee_id")
        if not target_employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_employee_id is required when manager submits feedback"
            )
        
        employee = await db.users.find_one({
            "employee_id": target_employee_id,
            "manager_id": current_user.employee_id,
            "role": UserRole.EMPLOYEE
        })
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found or not in your team"
            )
        
        employee_id = target_employee_id
        manager_id = current_user.employee_id
        
        form_data = {k: v for k, v in form_data.items() if k != "target_employee_id"}


    strengths = form_data.get("strengths", "Submitted via custom form")
    areas_to_improve = form_data.get("areas_to_improve", "Submitted via custom form")
    overall_sentiment = form_data.get("overall_sentiment", "neutral")
    additional_notes = form_data.get("additional_notes", f"Submitted using form: {form['title']}")
    

    feedback_dict = {
        "employee_id": employee_id,
        "manager_id": manager_id,
        "strengths": strengths,
        "areas_to_improve": areas_to_improve,
        "overall_sentiment": overall_sentiment,
        "additional_notes": additional_notes,
        "form_data": form_data, 
        "form_id": str(form["_id"]),  
        "created_at": datetime.utcnow(),
        "is_acknowledged": False
    }
    
    result = await db.feedback.insert_one(feedback_dict)
    created_feedback = await db.feedback.find_one({"_id": result.inserted_id})
    
    return FeedbackResponse(**created_feedback)


@router.get("/{form_id}/submissions", response_model=List[FeedbackResponse])
async def get_form_submissions(
    form_id: str,
    request: Request,
    current_user: UserResponse = Depends(get_current_manager),
    db = Depends(get_database)
):
    """Get all feedback submissions for a specific form (managers only)"""
    if not ObjectId.is_valid(form_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid form ID"
        )
    
    form = await db.forms.find_one({"_id": ObjectId(form_id)})
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Form not found"
        )
    
    if form["manager_id"] != current_user.employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view submissions for forms you've created"
        )
    
    submissions = await db.feedback.find({
        "form_id": form_id
    }).sort("created_at", -1).to_list(None)
    
    return [FeedbackResponse(**submission) for submission in submissions]
