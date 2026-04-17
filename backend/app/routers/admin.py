# backend/app/routers/admin.py
# 管理员端路由：学生档案管理 & 数据大屏

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentFeature

router = APIRouter(prefix="/api/v1", tags=["管理后台"])


# ==========================================
# 查询所有已录入的学生档案
# ==========================================
@router.get("/students")
async def get_all_students(db: Session = Depends(get_db)):
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


# ==========================================
# 删除指定学生的档案
# ==========================================
@router.delete("/students/{student_id}")
async def delete_student(student_id: str, db: Session = Depends(get_db)):
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
