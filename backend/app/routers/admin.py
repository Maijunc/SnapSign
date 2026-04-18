# backend/app/routers/admin.py
# 管理员端路由：用户管理 CRUD & 学生档案管理

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentFeature, User
from app.schemas import UserCreate, UserUpdate, UserOut
from app.auth import get_current_user, require_role, hash_password

router = APIRouter(prefix="/api/v1", tags=["管理后台"])


# ==========================================
# 用户管理 CRUD（仅管理员）
# ==========================================

@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.post("/users", response_model=UserOut)
async def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if data.role not in ("student", "teacher", "admin"):
        raise HTTPException(status_code=400, detail="角色必须是 student / teacher / admin")
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        real_name=data.real_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if data.real_name is not None:
        user.real_name = data.real_name
    if data.role is not None:
        if data.role not in ("student", "teacher", "admin"):
            raise HTTPException(status_code=400, detail="角色必须是 student / teacher / admin")
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"已删除用户 {user.real_name}"}


# ==========================================
# 学生人脸档案管理（教师 / 管理员）
# ==========================================

@router.get("/students")
async def get_all_students(
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "teacher")),
):
    try:
        students = db.query(
            StudentFeature.id,
            StudentFeature.student_id,
            StudentFeature.name
        ).all()
        result = [{"id": s.id, "student_id": s.student_id, "name": s.name} for s in students]
        return {"status": "success", "data": result}
    except Exception as e:
        print("❌ 查询学生列表失败:", str(e))
        raise HTTPException(status_code=500, detail="查询数据库失败")


@router.delete("/students/{student_id}")
async def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "teacher")),
):
    try:
        student = db.query(StudentFeature).filter(StudentFeature.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="未找到该学生档案")

        db.delete(student)
        db.commit()
        print(f"🗑️ 成功删除学生档案: {student.name} ({student_id})")
        return {"status": "success", "message": f"成功删除 {student.name} 的档案"}
    except HTTPException:
        raise
    except Exception as e:
        print("❌ 删除学生失败:", str(e))
        raise HTTPException(status_code=500, detail="删除数据库记录失败")
