# backend/app/routers/auth.py
# 认证路由：登录 / 获取当前用户信息

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    """用户名 + 密码登录，成功返回 JWT Token"""
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")

    token = create_access_token(data={"sub": user.username, "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        real_name=user.real_name,
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """根据 Token 获取当前登录用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "real_name": current_user.real_name,
        "role": current_user.role,
    }
