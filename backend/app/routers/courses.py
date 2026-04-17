# backend/app/routers/courses.py
# 课程排课管理路由：班级 / 课程 / 排课 CRUD + 考勤记录查询

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Course, CourseSchedule, AttendanceRecord, User
from app.schemas import (
    ClassCreate, ClassOut,
    CourseCreate, CourseOut,
    ScheduleCreate, ScheduleOut,
    AttendanceRecordOut,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1", tags=["课程排课"])


# ==========================================
# 班级
# ==========================================

@router.post("/classes", response_model=ClassOut)
async def create_class(
    data: ClassCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    if db.query(Class).filter(Class.name == data.name).first():
        raise HTTPException(status_code=400, detail="班级名称已存在")
    cls = Class(name=data.name)
    db.add(cls)
    db.commit()
    db.refresh(cls)
    return cls


@router.get("/classes", response_model=List[ClassOut])
async def list_classes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Class).all()


# ==========================================
# 课程
# ==========================================

@router.post("/courses", response_model=CourseOut)
async def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    teacher = db.query(User).filter(User.id == data.teacher_id, User.role == "teacher").first()
    if not teacher:
        raise HTTPException(status_code=400, detail="指定的教师不存在")

    course = Course(name=data.name, teacher_id=data.teacher_id)

    # 关联班级
    if data.class_ids:
        classes = db.query(Class).filter(Class.id.in_(data.class_ids)).all()
        if len(classes) != len(data.class_ids):
            raise HTTPException(status_code=400, detail="部分班级ID不存在")
        course.classes = classes

    db.add(course)
    db.commit()
    db.refresh(course)
    return _course_to_out(course)


@router.get("/courses", response_model=List[CourseOut])
async def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """教师只看自己的课程，管理员看全部"""
    query = db.query(Course)
    if current_user.role == "teacher":
        query = query.filter(Course.teacher_id == current_user.id)
    courses = query.all()
    return [_course_to_out(c) for c in courses]


@router.get("/courses/{course_id}/schedules", response_model=List[ScheduleOut])
async def list_course_schedules(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return [_schedule_to_out(s) for s in course.schedules]


# ==========================================
# 排课
# ==========================================

@router.post("/schedules", response_model=ScheduleOut)
async def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    if not db.query(Course).filter(Course.id == data.course_id).first():
        raise HTTPException(status_code=400, detail="课程不存在")
    if not db.query(Class).filter(Class.id == data.class_id).first():
        raise HTTPException(status_code=400, detail="班级不存在")
    if not (1 <= data.weekday <= 7):
        raise HTTPException(status_code=400, detail="weekday 必须在 1-7 之间")

    schedule = CourseSchedule(
        course_id=data.course_id,
        class_id=data.class_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _schedule_to_out(schedule)


@router.get("/schedules/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")
    return _schedule_to_out(schedule)


# ==========================================
# 考勤记录查询
# ==========================================

@router.get("/attendance/{schedule_id}", response_model=List[AttendanceRecordOut])
async def list_attendance(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.schedule_id == schedule_id)
        .order_by(AttendanceRecord.check_in_time.desc())
        .all()
    )
    return records


# ==========================================
# 辅助函数：ORM → Pydantic 手动映射
# ==========================================

def _course_to_out(course: Course) -> CourseOut:
    return CourseOut(
        id=course.id,
        name=course.name,
        teacher_id=course.teacher_id,
        teacher_name=course.teacher.real_name if course.teacher else None,
        classes=[ClassOut.model_validate(c) for c in course.classes],
    )


def _schedule_to_out(s: CourseSchedule) -> ScheduleOut:
    return ScheduleOut(
        id=s.id,
        course_id=s.course_id,
        class_id=s.class_id,
        course_name=s.course.name if s.course else None,
        class_name=s.class_.name if s.class_ else None,
        weekday=s.weekday,
        start_time=s.start_time,
        end_time=s.end_time,
        location=s.location,
    )
