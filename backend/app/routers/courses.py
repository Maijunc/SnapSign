# backend/app/routers/courses.py
# 课程排课管理路由：班级 / 课程 / 排课 CRUD + 考勤记录查询 + 节假日 + 班级学生

from datetime import timedelta, date, datetime
from typing import List
import calendar as _cal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Class, Course, CourseSchedule, AttendanceRecord, User, StudentFeature, Holiday, Appeal, LeaveRequest, schedule_classes
from app.schemas import (
    ClassCreate, ClassOut, ClassUpdate,
    CourseCreate, CourseOut, CourseUpdate,
    ScheduleCreate, ScheduleOut, ScheduleUpdate, ScheduleWeekOut,
    AttendanceRecordOut,
    MyAttendanceOut, MyAttendancePageOut,
    HolidayCreate, HolidayOut,
    ClassStudentsAdd, StudentFeatureOut,
    CalendarEvent, CalendarDayOut,
    MyCourseOut, MyCourseScheduleOut,
    AppealCreate, AppealOut,
    LeaveCreate, LeaveOut,
    ReviewAction,
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/v1", tags=["课程排课"])


def _is_schedule_active_on_date(schedule: CourseSchedule, target_date: date) -> bool:
    if target_date.isoweekday() != schedule.weekday:
        return False
    if schedule.start_date and schedule.total_weeks:
        end_date = schedule.start_date + timedelta(weeks=schedule.total_weeks)
        if target_date < schedule.start_date or target_date >= end_date:
            return False
    return True


def _schedule_class_ids(schedule: CourseSchedule) -> list[int]:
    return schedule.resolved_class_ids


def _schedule_class_names(schedule: CourseSchedule) -> list[str]:
    return schedule.resolved_class_names


def _schedule_class_name(schedule: CourseSchedule) -> str:
    return schedule.resolved_class_name or "未知班级"


def _schedule_has_any_class(schedule: CourseSchedule, class_ids: set[int]) -> bool:
    return bool(class_ids.intersection(_schedule_class_ids(schedule)))


def _mark_absent_for_schedule_date(db: Session, schedule: CourseSchedule, target_date: date) -> int:
    """Idempotent absent marking for a specific schedule on a specific date."""
    students = schedule.resolved_students
    if not students:
        return 0
    if not _is_schedule_active_on_date(schedule, target_date):
        return 0

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date, datetime.max.time())

    # 今日已签到（正常/迟到）
    signed_ids = set(
        r.student_feature_id for r in
        db.query(AttendanceRecord.student_feature_id)
        .filter(
            AttendanceRecord.schedule_id == schedule.id,
            AttendanceRecord.status.in_(["present", "late"]),
            AttendanceRecord.check_in_time.between(day_start, day_end),
        )
        .all()
    )

    # 今日已存在的缺勤记录（避免重复写入）
    absent_ids = set(
        r.student_feature_id for r in
        db.query(AttendanceRecord.student_feature_id)
        .filter(
            AttendanceRecord.schedule_id == schedule.id,
            AttendanceRecord.status == "absent",
            AttendanceRecord.created_at.between(day_start, day_end),
        )
        .all()
    )

    absent_count = 0
    for student in students:
        if student.id in signed_ids or student.id in absent_ids:
            continue
        record = AttendanceRecord(
            schedule_id=schedule.id,
            student_feature_id=student.id,
            student_name=student.name,
            check_in_time=None,
            status="absent",
            face_distance=None,
        )
        db.add(record)
        absent_count += 1

    if absent_count > 0:
        db.commit()
    return absent_count


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


@router.put("/classes/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: int,
    data: ClassUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    if data.name is not None:
        if db.query(Class).filter(Class.name == data.name, Class.id != class_id).first():
            raise HTTPException(status_code=400, detail="班级名称已存在")
        cls.name = data.name
    db.commit()
    db.refresh(cls)
    return cls


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    # 检查是否有关联排课
    has_schedule = db.query(CourseSchedule).filter(CourseSchedule.class_id == class_id).first()
    has_shared_schedule = db.execute(
        schedule_classes.select().where(schedule_classes.c.class_id == class_id)
    ).first()
    if has_schedule or has_shared_schedule:
        raise HTTPException(status_code=400, detail="该班级下仍有排课，请先删除相关排课")
    db.delete(cls)
    db.commit()
    return {"status": "success", "message": f"已删除班级 {cls.name}"}


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


@router.get("/courses/my", response_model=List[MyCourseOut])
async def my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生查看自己所在班级关联的课程及排课信息"""
    sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not sf or not sf.classes:
        return []

    result = []
    for cls in sf.classes:
        for course in cls.courses:
            schedules = [
                s for s in db.query(CourseSchedule).filter(CourseSchedule.course_id == course.id).all()
                if cls.id in _schedule_class_ids(s)
            ]
            result.append(MyCourseOut(
                course_id=course.id,
                course_name=course.name,
                teacher_name=course.teacher.real_name if course.teacher else None,
                class_name=cls.name,
                schedules=[
                    MyCourseScheduleOut(
                        schedule_id=s.id,
                        weekday=s.weekday,
                        start_time=s.start_time,
                        end_time=s.end_time,
                        location=s.location,
                    )
                    for s in schedules
                ],
            ))
    return result


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


@router.put("/courses/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: int,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if data.name is not None:
        course.name = data.name
    if data.teacher_id is not None:
        teacher = db.query(User).filter(User.id == data.teacher_id, User.role == "teacher").first()
        if not teacher:
            raise HTTPException(status_code=400, detail="指定的教师不存在")
        course.teacher_id = data.teacher_id
    if data.class_ids is not None:
        classes = db.query(Class).filter(Class.id.in_(data.class_ids)).all()
        if len(classes) != len(data.class_ids):
            raise HTTPException(status_code=400, detail="部分班级ID不存在")
        course.classes = classes
    db.commit()
    db.refresh(course)
    return _course_to_out(course)


@router.delete("/courses/{course_id}")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    # 检查是否有关联排课
    if db.query(CourseSchedule).filter(CourseSchedule.course_id == course_id).first():
        raise HTTPException(status_code=400, detail="该课程下仍有排课，请先删除相关排课")
    db.delete(course)
    db.commit()
    return {"status": "success", "message": f"已删除课程 {course.name}"}


# ==========================================
# 排课
# ==========================================

@router.post("/schedules", response_model=ScheduleOut)
async def create_schedule(
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    course = db.query(Course).filter(Course.id == data.course_id).first()
    if not course:
        raise HTTPException(status_code=400, detail="课程不存在")

    target_class_ids = list(dict.fromkeys(data.class_ids or ([] if data.class_id is None else [data.class_id])))
    if not target_class_ids:
        raise HTTPException(status_code=400, detail="至少选择一个班级")

    classes = db.query(Class).filter(Class.id.in_(target_class_ids)).all()
    if len(classes) != len(target_class_ids):
        raise HTTPException(status_code=400, detail="部分班级不存在")
    if data.total_weeks < 1 or data.total_weeks > 30:
        raise HTTPException(status_code=400, detail="持续周数必须在 1-30 之间")

    # weekday 从 start_date 自动推算（Python: 0=周一, isoweekday: 1=周一）
    weekday = data.start_date.isoweekday()

    # 排课冲突检测：任一目标班级在同一星期、时间段重叠
    conflict_candidates = db.query(CourseSchedule).filter(
        CourseSchedule.weekday == weekday,
        CourseSchedule.start_time < data.end_time,
        CourseSchedule.end_time > data.start_time,
    ).all()
    conflicts = [s for s in conflict_candidates if set(_schedule_class_ids(s)).intersection(target_class_ids)]
    if conflicts:
        raise HTTPException(
            status_code=400,
            detail=f"排课冲突：所选班级中存在班级在{['','周一','周二','周三','周四','周五','周六','周日'][weekday]}已有课程时间段重叠",
        )

    schedule = CourseSchedule(
        course_id=data.course_id,
        class_id=target_class_ids[0],
        weekday=weekday,
        start_date=data.start_date,
        total_weeks=data.total_weeks,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
    )
    db.add(schedule)
    db.flush()
    schedule.classes = sorted(classes, key=lambda cls: target_class_ids.index(cls.id))
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


@router.put("/schedules/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")
    if data.start_date is not None:
        schedule.start_date = data.start_date
        schedule.weekday = data.start_date.isoweekday()
    if data.total_weeks is not None:
        if data.total_weeks < 1 or data.total_weeks > 30:
            raise HTTPException(status_code=400, detail="持续周数必须在 1-30 之间")
        schedule.total_weeks = data.total_weeks
    if data.start_time is not None:
        schedule.start_time = data.start_time
    if data.end_time is not None:
        schedule.end_time = data.end_time
    if data.location is not None:
        schedule.location = data.location
    db.commit()
    db.refresh(schedule)
    return _schedule_to_out(schedule)


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")
    # 删除关联的考勤记录
    db.query(AttendanceRecord).filter(AttendanceRecord.schedule_id == schedule_id).delete()
    db.delete(schedule)
    db.commit()
    return {"status": "success", "message": "已删除排课"}


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
        schedules = [
            s for s in db.query(CourseSchedule).all()
            if _schedule_has_any_class(s, set(my_class_ids))
        ] if my_class_ids else []

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
                class_name=_schedule_class_name(s),
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
    result = []
    for s in cls.students:
        out = StudentFeatureOut.model_validate(s)
        out.has_face = s.face_encoding is not None
        result.append(out)
    return result


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

@router.get("/attendance/my", response_model=MyAttendancePageOut)
async def my_attendance(
    course_id: int = Query(None, description="按课程筛选"),
    status: str = Query(None, description="按状态筛选: present/late/absent"),
    start_date: date = Query(None, description="开始日期"),
    end_date: date = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生查询自己的考勤记录（支持筛选+分页）"""
    feature = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not feature:
        return MyAttendancePageOut(total=0, page=page, page_size=page_size, items=[])

    query = db.query(AttendanceRecord).filter(AttendanceRecord.student_feature_id == feature.id)

    # 按课程筛选
    if course_id is not None:
        schedule_ids = [
            s.id for s in db.query(CourseSchedule.id).filter(CourseSchedule.course_id == course_id).all()
        ]
        query = query.filter(AttendanceRecord.schedule_id.in_(schedule_ids)) if schedule_ids else query.filter(False)

    # 按状态筛选
    if status:
        query = query.filter(AttendanceRecord.status == status)

    # 按日期范围筛选
    if start_date:
        from datetime import datetime as _dt
        query = query.filter(AttendanceRecord.check_in_time >= _dt.combine(start_date, _dt.min.time()))
    if end_date:
        from datetime import datetime as _dt
        query = query.filter(AttendanceRecord.check_in_time <= _dt.combine(end_date, _dt.max.time()))

    total = query.count()
    records = (
        query.order_by(AttendanceRecord.check_in_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        schedule = r.schedule
        items.append(MyAttendanceOut(
            id=r.id,
            schedule_id=r.schedule_id,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=_schedule_class_name(schedule) if schedule else None,
            check_in_time=r.check_in_time,
            status=r.status,
            face_distance=r.face_distance,
        ))

    return MyAttendancePageOut(total=total, page=page, page_size=page_size, items=items)


@router.get("/attendance/{schedule_id}", response_model=List[AttendanceRecordOut])
async def list_attendance(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # 自动补记：若已过下课时间，按今日课次补齐缺勤
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if schedule:
        now = datetime.now()
        if _is_schedule_active_on_date(schedule, now.date()) and now.time() >= schedule.end_time:
            _mark_absent_for_schedule_date(db, schedule, now.date())

    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.schedule_id == schedule_id)
        .order_by(AttendanceRecord.check_in_time.desc())
        .all()
    )
    return records


# ==========================================
# 缺勤自动标记（将某排课未签到学生标为 absent）
# ==========================================

@router.post("/attendance/{schedule_id}/mark_absent")
async def mark_absent(
    schedule_id: int,
    attendance_date: date = Query(None, description="课次日期，默认今天"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "teacher")),
):
    """课后手动触发：将未签到学生补记为缺勤（按日期、幂等）"""
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")

    target_date = attendance_date or date.today()
    if not _is_schedule_active_on_date(schedule, target_date):
        raise HTTPException(status_code=400, detail="该日期不在此排课的有效上课范围内")

    if target_date == date.today() and datetime.now().time() < schedule.end_time:
        raise HTTPException(status_code=400, detail="未到下课时间，暂不允许补记缺勤")

    absent_count = _mark_absent_for_schedule_date(db, schedule, target_date)
    return {
        "status": "success",
        "message": f"已补记 {absent_count} 名学生为缺勤",
        "attendance_date": str(target_date),
    }


# ==========================================
# 学生申诉
# ==========================================

@router.post("/attendance/appeal", response_model=AppealOut)
async def create_appeal(
    data: AppealCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生提交考勤申诉"""
    # 验证考勤记录存在且属于当前学生
    record = db.query(AttendanceRecord).filter(AttendanceRecord.id == data.attendance_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="考勤记录不存在")
    sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not sf or record.student_feature_id != sf.id:
        raise HTTPException(status_code=403, detail="无权申诉此记录")
    # 检查是否已有申诉
    existing = db.query(Appeal).filter(Appeal.attendance_id == data.attendance_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该记录已提交过申诉")
    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="申诉理由不能为空")

    appeal = Appeal(
        attendance_id=data.attendance_id,
        user_id=current_user.id,
        reason=data.reason.strip(),
    )
    db.add(appeal)
    db.commit()
    db.refresh(appeal)

    schedule = record.schedule
    return AppealOut(
        id=appeal.id,
        attendance_id=appeal.attendance_id,
        reason=appeal.reason,
        status=appeal.status,
        reply=appeal.reply,
        created_at=appeal.created_at,
        course_name=schedule.course.name if schedule and schedule.course else None,
        class_name=_schedule_class_name(schedule) if schedule else None,
        student_name=current_user.real_name,
        original_status=record.status,
        check_in_time=record.check_in_time,
    )


@router.get("/attendance/my_appeals", response_model=List[AppealOut])
async def my_appeals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生查看自己的所有申诉"""
    appeals = (
        db.query(Appeal)
        .filter(Appeal.user_id == current_user.id)
        .order_by(Appeal.created_at.desc())
        .all()
    )
    result = []
    for a in appeals:
        record = a.attendance_record
        schedule = record.schedule if record else None
        result.append(AppealOut(
            id=a.id,
            attendance_id=a.attendance_id,
            reason=a.reason,
            status=a.status,
            reply=a.reply,
            created_at=a.created_at,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=_schedule_class_name(schedule) if schedule else None,
            student_name=a.user.real_name if a.user else None,
            original_status=record.status if record else None,
            check_in_time=record.check_in_time if record else None,
        ))
    return result


# ==========================================
# 学生请假
# ==========================================

@router.post("/leave", response_model=LeaveOut)
async def create_leave(
    data: LeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生提交请假申请"""
    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == data.schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")
    # 验证学生属于该排课班级
    sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not sf:
        raise HTTPException(status_code=403, detail="学生信息未关联")
    my_class_ids = {c.id for c in sf.classes}
    if not _schedule_has_any_class(schedule, my_class_ids):
        raise HTTPException(status_code=403, detail="你不属于该课程班级")
    if not data.reason.strip():
        raise HTTPException(status_code=400, detail="请假理由不能为空")
    # 检查是否已提交过相同排课+日期的请假
    existing = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == current_user.id,
        LeaveRequest.schedule_id == data.schedule_id,
        LeaveRequest.leave_date == data.leave_date,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该课次已提交过请假申请")

    leave = LeaveRequest(
        user_id=current_user.id,
        schedule_id=data.schedule_id,
        leave_date=data.leave_date,
        reason=data.reason.strip(),
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)

    return LeaveOut(
        id=leave.id,
        schedule_id=leave.schedule_id,
        leave_date=leave.leave_date,
        reason=leave.reason,
        status=leave.status,
        reply=leave.reply,
        created_at=leave.created_at,
        course_name=schedule.course.name if schedule.course else None,
        class_name=_schedule_class_name(schedule),
        student_name=current_user.real_name,
    )


@router.get("/leave/my", response_model=List[LeaveOut])
async def my_leaves(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生查看自己的所有请假记录"""
    leaves = (
        db.query(LeaveRequest)
        .filter(LeaveRequest.user_id == current_user.id)
        .order_by(LeaveRequest.created_at.desc())
        .all()
    )
    result = []
    for lv in leaves:
        schedule = lv.schedule
        result.append(LeaveOut(
            id=lv.id,
            schedule_id=lv.schedule_id,
            leave_date=lv.leave_date,
            reason=lv.reason,
            status=lv.status,
            reply=lv.reply,
            created_at=lv.created_at,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=_schedule_class_name(schedule) if schedule else None,
            student_name=lv.user.real_name if lv.user else None,
        ))
    return result


# ==========================================
# 教师审批：考勤申诉
# ==========================================

def _get_teacher_course_ids(db: Session, teacher: User) -> list[int]:
    """获取教师名下所有课程 ID"""
    return [c.id for c in db.query(Course.id).filter(Course.teacher_id == teacher.id).all()]


@router.get("/appeals/pending", response_model=List[AppealOut])
async def list_appeals_for_teacher(
    status: str = Query("pending", description="过滤状态: pending/approved/rejected/all"),
    course_id: int = Query(None, description="按课程过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    """教师查看自己课程下的考勤申诉"""
    my_course_ids = _get_teacher_course_ids(db, current_user)
    if not my_course_ids:
        return []

    # 筛选属于该教师课程的排课 ID
    schedule_ids_q = db.query(CourseSchedule.id).filter(CourseSchedule.course_id.in_(my_course_ids))
    if course_id:
        schedule_ids_q = schedule_ids_q.filter(CourseSchedule.course_id == course_id)
    my_schedule_ids = [s.id for s in schedule_ids_q.all()]
    if not my_schedule_ids:
        return []

    # 根据 schedule_id 找考勤记录，再找申诉
    record_ids = [
        r.id for r in
        db.query(AttendanceRecord.id).filter(AttendanceRecord.schedule_id.in_(my_schedule_ids)).all()
    ]
    if not record_ids:
        return []

    q = db.query(Appeal).filter(Appeal.attendance_id.in_(record_ids))
    if status != "all":
        q = q.filter(Appeal.status == status)
    appeals = q.order_by(Appeal.created_at.desc()).all()

    result = []
    for a in appeals:
        record = a.attendance_record
        schedule = record.schedule if record else None
        result.append(AppealOut(
            id=a.id,
            attendance_id=a.attendance_id,
            reason=a.reason,
            status=a.status,
            reply=a.reply,
            created_at=a.created_at,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=_schedule_class_name(schedule) if schedule else None,
            student_name=a.user.real_name if a.user else None,
            original_status=record.status if record else None,
            check_in_time=record.check_in_time if record else None,
        ))
    return result


@router.put("/appeals/{appeal_id}/review")
async def review_appeal(
    appeal_id: int,
    data: ReviewAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    """教师审批申诉"""
    if data.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="action 必须是 approved 或 rejected")

    appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
    if not appeal:
        raise HTTPException(status_code=404, detail="申诉记录不存在")
    if appeal.status != "pending":
        raise HTTPException(status_code=400, detail="该申诉已审批")

    # 校验该申诉属于该教师的课程
    record = appeal.attendance_record
    if not record or not record.schedule:
        raise HTTPException(status_code=400, detail="考勤记录异常")
    if record.schedule.course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权审批此申诉")

    appeal.status = data.action
    appeal.reply = data.reply.strip() if data.reply else None

    # 申诉通过时自动将考勤状态改为 present
    if data.action == "approved":
        record.status = "present"

    db.commit()
    return {"status": "success", "message": f"申诉已{'通过' if data.action == 'approved' else '拒绝'}"}


# ==========================================
# 教师审批：请假申请
# ==========================================

@router.get("/leaves/pending", response_model=List[LeaveOut])
async def list_leaves_for_teacher(
    status: str = Query("pending", description="过滤状态: pending/approved/rejected/all"),
    course_id: int = Query(None, description="按课程过滤"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    """教师查看自己课程下的请假申请"""
    my_course_ids = _get_teacher_course_ids(db, current_user)
    if not my_course_ids:
        return []

    q = (
        db.query(LeaveRequest)
        .join(CourseSchedule, LeaveRequest.schedule_id == CourseSchedule.id)
        .filter(CourseSchedule.course_id.in_(my_course_ids))
    )
    if course_id:
        q = q.filter(CourseSchedule.course_id == course_id)
    if status != "all":
        q = q.filter(LeaveRequest.status == status)
    leaves = q.order_by(LeaveRequest.created_at.desc()).all()

    result = []
    for lv in leaves:
        schedule = lv.schedule
        result.append(LeaveOut(
            id=lv.id,
            schedule_id=lv.schedule_id,
            leave_date=lv.leave_date,
            reason=lv.reason,
            status=lv.status,
            reply=lv.reply,
            created_at=lv.created_at,
            course_name=schedule.course.name if schedule and schedule.course else None,
            class_name=_schedule_class_name(schedule) if schedule else None,
            student_name=lv.user.real_name if lv.user else None,
        ))
    return result


@router.put("/leaves/{leave_id}/review")
async def review_leave(
    leave_id: int,
    data: ReviewAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("teacher")),
):
    """教师审批请假"""
    if data.action not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="action 必须是 approved 或 rejected")

    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="请假记录不存在")
    if leave.status != "pending":
        raise HTTPException(status_code=400, detail="该请假已审批")

    # 校验该请假属于该教师的课程
    schedule = leave.schedule
    if not schedule or not schedule.course:
        raise HTTPException(status_code=400, detail="排课信息异常")
    if schedule.course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权审批此请假")

    leave.status = data.action
    leave.reply = data.reply.strip() if data.reply else None
    db.commit()
    return {"status": "success", "message": f"请假已{'通过' if data.action == 'approved' else '拒绝'}"}


# ==========================================
# 考勤数据导出 Excel
# ==========================================

@router.get("/attendance/{schedule_id}/export")
async def export_attendance(
    schedule_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin", "teacher")),
):
    """导出某排课的考勤记录为 Excel"""
    import io
    from fastapi.responses import StreamingResponse

    schedule = db.query(CourseSchedule).filter(CourseSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="排课不存在")

    # 自动补记：导出前若已过下课时间，先补齐今日缺勤
    now = datetime.now()
    if _is_schedule_active_on_date(schedule, now.date()) and now.time() >= schedule.end_time:
        _mark_absent_for_schedule_date(db, schedule, now.date())

    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.schedule_id == schedule_id)
        .order_by(AttendanceRecord.check_in_time)
        .all()
    )

    course_name = schedule.course.name if schedule.course else "未知课程"
    class_name = _schedule_class_name(schedule)

    # 构建 CSV（兼容性最好，无需额外依赖）
    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel Chinese support
    output.write(f"课程：{course_name}，班级：{class_name}\n")
    output.write("学号,姓名,签到时间,状态,匹配距离\n")

    status_map = {"present": "正常", "late": "迟到", "absent": "缺勤"}
    for r in records:
        # 从 student_feature 获取学号
        sf = db.query(StudentFeature).filter(StudentFeature.id == r.student_feature_id).first()
        student_id = sf.student_id if sf else ""
        check_time = r.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if r.check_in_time else "未签到"
        distance = f"{r.face_distance:.3f}" if r.face_distance is not None else "-"
        output.write(f"{student_id},{r.student_name or ''},{check_time},{status_map.get(r.status, r.status)},{distance}\n")

    output.seek(0)
    filename = f"attendance_{course_name}_{class_name}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


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
        class_ids=_schedule_class_ids(s),
        course_name=s.course.name if s.course else None,
        class_name=_schedule_class_name(s),
        class_names=_schedule_class_names(s),
        weekday=s.weekday,
        start_date=s.start_date,
        total_weeks=s.total_weeks,
        start_time=s.start_time,
        end_time=s.end_time,
        location=s.location,
    )
