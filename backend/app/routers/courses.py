# backend/app/routers/courses.py
# 课程排课管理路由：班级 / 课程 / 排课 CRUD + 考勤记录查询 + 节假日 + 班级学生

from datetime import timedelta, date
from typing import List
import calendar as _cal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Course, CourseSchedule, AttendanceRecord, User, StudentFeature, Holiday
from app.schemas import (
    ClassCreate, ClassOut,
    CourseCreate, CourseOut,
    ScheduleCreate, ScheduleOut, ScheduleWeekOut,
    AttendanceRecordOut,
    MyAttendanceOut,
    HolidayCreate, HolidayOut,
    ClassStudentsAdd, StudentFeatureOut,
    CalendarEvent, CalendarDayOut,
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
    if data.total_weeks < 1 or data.total_weeks > 30:
        raise HTTPException(status_code=400, detail="持续周数必须在 1-30 之间")

    # weekday 从 start_date 自动推算（Python: 0=周一, isoweekday: 1=周一）
    weekday = data.start_date.isoweekday()

    schedule = CourseSchedule(
        course_id=data.course_id,
        class_id=data.class_id,
        weekday=weekday,
        start_date=data.start_date,
        total_weeks=data.total_weeks,
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
# 排课周次展开（含节假日标注）
# ==========================================

@router.get("/schedules/{schedule_id}/weeks", response_model=List[ScheduleWeekOut])
async def get_schedule_weeks(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """展开排课的每一周，标注节假日"""
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")

    # 查询所有节假日（date → name）
    holidays = {h.holiday_date: h.name for h in db.query(Holiday).all()}

    weeks = []
    for i in range(schedule.total_weeks):
        d = schedule.start_date + timedelta(weeks=i)
        is_holiday = d in holidays
        weeks.append(ScheduleWeekOut(
            week=i + 1,
            date=d,
            is_holiday=is_holiday,
            holiday_name=holidays.get(d),
        ))
    return weeks


# ==========================================
# 节假日管理
# ==========================================

@router.post("/holidays", response_model=HolidayOut)
async def create_holiday(
    data: HolidayCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    if db.query(Holiday).filter(Holiday.holiday_date == data.holiday_date).first():
        raise HTTPException(status_code=400, detail="该日期已存在节假日")
    h = Holiday(holiday_date=data.holiday_date, name=data.name)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


@router.get("/holidays", response_model=List[HolidayOut])
async def list_holidays(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Holiday).order_by(Holiday.holiday_date).all()


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    h = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="节假日不存在")
    db.delete(h)
    db.commit()
    return {"status": "success", "message": f"已删除 {h.name}"}


# ==========================================
# 教学日历（教师 / 学生通用）
# ==========================================

@router.get("/calendar", response_model=List[CalendarDayOut])
async def get_calendar(
    year: int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回指定年月的教学日历。
    教师：看自己教的课程排课；学生：看自己所在班级的排课；管理员：看全部。
    """
    # 1. 收集当前用户可见的排课
    if current_user.role == "admin":
        schedules = db.query(CourseSchedule).all()
    elif current_user.role == "teacher":
        my_course_ids = [c.id for c in db.query(Course).filter(Course.teacher_id == current_user.id).all()]
        schedules = db.query(CourseSchedule).filter(
            CourseSchedule.course_id.in_(my_course_ids)
        ).all() if my_course_ids else []
    else:
        # student: 通过 user_id → StudentFeature → classes → schedules
        sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
        if not sf or not sf.classes:
            return []
        my_class_ids = [c.id for c in sf.classes]
        schedules = db.query(CourseSchedule).filter(
            CourseSchedule.class_id.in_(my_class_ids)
        ).all() if my_class_ids else []

    if not schedules:
        return []

    # 2. 按 weekday 分组
    weekday_map: dict[int, list[CourseSchedule]] = {}
    for s in schedules:
        weekday_map.setdefault(s.weekday, []).append(s)

    # 3. 查节假日
    _, days_in_month = _cal.monthrange(year, month)
    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)
    holidays = {
        h.holiday_date: h.name
        for h in db.query(Holiday).filter(
            Holiday.holiday_date >= first_day,
            Holiday.holiday_date <= last_day,
        ).all()
    }

    # 4. 遍历该月每一天
    result = []
    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        iso_wd = d.isoweekday()  # 1=Mon
        day_schedules = weekday_map.get(iso_wd, [])
        is_holiday = d in holidays

        # 筛选：这天在排课的有效周数范围内
        events = []
        for s in day_schedules:
            if s.start_date and s.total_weeks:
                end_date = s.start_date + timedelta(weeks=s.total_weeks)
                if d < s.start_date or d >= end_date:
                    continue
            events.append(CalendarEvent(
                schedule_id=s.id,
                course_name=s.course.name if s.course else "",
                class_name=s.class_.name if s.class_ else "",
                start_time=s.start_time.strftime("%H:%M"),
                end_time=s.end_time.strftime("%H:%M"),
                location=s.location,
                is_holiday=is_holiday,
                holiday_name=holidays.get(d),
            ))

        if events:
            result.append(CalendarDayOut(date=d, events=events))

    return result


# ==========================================
# 班级学生管理
# ==========================================

@router.get("/classes/{class_id}/students", response_model=List[StudentFeatureOut])
async def list_class_students(
    class_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "teacher")),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    return [StudentFeatureOut.model_validate(s) for s in cls.students]


@router.post("/classes/{class_id}/students")
async def add_students_to_class(
    class_id: int,
    data: ClassStudentsAdd,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    existing_ids = {s.id for s in cls.students}
    added = 0
    for sid in data.student_feature_ids:
        if sid in existing_ids:
            continue
        sf = db.query(StudentFeature).filter(StudentFeature.id == sid).first()
        if sf:
            cls.students.append(sf)
            added += 1
    db.commit()
    return {"status": "success", "message": f"已添加 {added} 名学生"}


@router.delete("/classes/{class_id}/students/{student_feature_id}")
async def remove_student_from_class(
    class_id: int,
    student_feature_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    sf = db.query(StudentFeature).filter(StudentFeature.id == student_feature_id).first()
    if sf and sf in cls.students:
        cls.students.remove(sf)
        db.commit()
        return {"status": "success", "message": "已移除学生"}
    raise HTTPException(status_code=404, detail="该学生不在此班级中")


# ==========================================
# 考勤记录查询
# ==========================================

@router.get("/attendance/my", response_model=List[MyAttendanceOut])
async def my_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生查询自己的所有考勤记录（通过 user_id → StudentFeature → AttendanceRecord）"""
    # 找到当前用户关联的人脸特征
    feature = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not feature:
        return []

    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.student_feature_id == feature.id)
        .order_by(AttendanceRecord.check_in_time.desc())
        .all()
    )

    result = []
    for r in records:
        schedule = r.schedule
        result.append(MyAttendanceOut(
            id=r.id,
            schedule_id=r.schedule_id,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=schedule.class_.name if schedule and schedule.class_ else None,
            check_in_time=r.check_in_time,
            status=r.status,
            face_distance=r.face_distance,
        ))
    return result


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
        start_date=s.start_date,
        total_weeks=s.total_weeks,
        start_time=s.start_time,
        end_time=s.end_time,
        location=s.location,
    )
