from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from typing import List
from datetime import timedelta
from database import get_database
from models import UserCreate, UserLogin, UserResponse, Token, UserRole, ManagerResponse
from auth_middleware import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
    set_auth_cookie,
    clear_auth_cookie
)
from datetime import datetime

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate, db = Depends(get_database)):
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_employee = await db.users.find_one({"employee_id": user.employee_id})
    if existing_employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID already exists"
        )
    
    if user.role == UserRole.EMPLOYEE and user.manager_id:
        manager = await db.users.find_one({
            "employee_id": user.manager_id,
            "role": UserRole.MANAGER
        })
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid manager ID"
            )
    
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["is_active"] = True
    
    result = await db.users.insert_one(user_dict)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return UserResponse(**created_user)

@router.post("/login")
async def login_user(
    user_credentials: UserLogin, 
    response: Response,
    db = Depends(get_database)
):
    user = await db.users.find_one({"email": user_credentials.email})
    
    if not user or not verify_password(user_credentials.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    set_auth_cookie(response, access_token)
    
    return {
        "message": "Login successful",
        "user": UserResponse(**user),
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout_user(response: Response):
    """Logout user by clearing the authentication cookie"""
    clear_auth_cookie(response)
    return {"message": "Logout successful"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    current_user: UserResponse = Depends(get_current_user)
):
    return current_user

@router.get("/team-members", response_model=List[UserResponse])
async def get_team_members(
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db = Depends(get_database)
):
    if current_user.role != UserRole.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can view team members"
        )
    
    team_members = await db.users.find({
        "manager_id": current_user.employee_id,
        "role": UserRole.EMPLOYEE,
        "is_active": True
    }).to_list(None)
    
    return [UserResponse(**member) for member in team_members]

@router.get("/manager", response_model=List[ManagerResponse])
async def get_managers(
    request: Request,
    db = Depends(get_database)
):
    cursor = db.users.find({"role": UserRole.MANAGER})
    managers = await cursor.to_list(length=None)

    if not managers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No managers found"
        )
    
    response = []
    for manager in managers:
        item = {
            "label": manager["full_name"],
            "value": manager["employee_id"]
        }
        response.append(item)
    
    return response


@router.get("/check-auth")
async def check_auth_status(
    request: Request,
    current_user: UserResponse = Depends(get_current_user)
):
    """Check if user is authenticated and return basic info"""
    return {
        "authenticated": True,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "employee_id": current_user.employee_id
        }
    }

@router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    current_user: UserResponse = Depends(get_current_user)
):
    """Refresh the authentication token/cookie"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=access_token_expires
    )
    
    set_auth_cookie(response, access_token)
    
    return {
        "message": "Token refreshed successfully",
        "access_token": access_token,
        "token_type": "bearer"
    }
