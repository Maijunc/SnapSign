# backend/app/routers/dashboard.py
# 数据大屏路由：统计卡片 / 出勤趋势 / 今日排课 / 实时考勤

from datetime import date, timedelta, datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User, Course, CourseSchedule, AttendanceRecord, StudentFeature, Class,
)
from app.schemas import DashboardStats, TrendItem, RecentActivity, ScheduleBrief
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["数据大屏"])


# ==========================================
# 统计卡片（4 个指标）
# ==========================================

@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    if current_user.role == "admin":
        card1_title = "学生档案总数"
        card1_value = db.query(func.count(StudentFeature.id)).scalar() or 0
        today_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.check_in_time.between(today_start, today_end)
        ).all()
    else:
        # teacher: 只统计自己课程相关
        card1_title = "我的课程数"
        card1_value = db.query(func.count(Course.id)).filter(Course.teacher_id == current_user.id).scalar() or 0
        my_course_ids = [c.id for c in db.query(Course.id).filter(Course.teacher_id == current_user.id).all()]
        my_schedule_ids = [
            s.id for s in db.query(CourseSchedule.id).filter(CourseSchedule.course_id.in_(my_course_ids)).all()
        ] if my_course_ids else []
        today_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.schedule_id.in_(my_schedule_ids),
            AttendanceRecord.check_in_time.between(today_start, today_end),
        ).all() if my_schedule_ids else []

    present_count = sum(1 for r in today_records if r.status == "present")
    late_count = sum(1 for r in today_records if r.status == "late")
    absent_count = sum(1 for r in today_records if r.status == "absent")

    return DashboardStats(
        card1_title=card1_title,
        card1_value=card1_value,
        card2_title="今日已签到",
        card2_value=present_count + late_count,
        card3_title="今日迟到",
        card3_value=late_count,
        card4_title="今日缺勤",
        card4_value=absent_count,
    )


# ==========================================
# 近 7 日出勤率趋势
# ==========================================

@router.get("/trend", response_model=List[TrendItem])
async def dashboard_trend(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        day_start = datetime.combine(d, datetime.min.time())
        day_end = datetime.combine(d, datetime.max.time())

        q = db.query(AttendanceRecord).filter(
            AttendanceRecord.check_in_time.between(day_start, day_end)
        )
        if current_user.role == "teacher":
            my_course_ids = [c.id for c in db.query(Course.id).filter(Course.teacher_id == current_user.id).all()]
            my_sched_ids = [
                s.id for s in db.query(CourseSchedule.id).filter(CourseSchedule.course_id.in_(my_course_ids)).all()
            ] if my_course_ids else []
            q = q.filter(AttendanceRecord.schedule_id.in_(my_sched_ids)) if my_sched_ids else q.filter(False)

        total = q.count()
        present = q.filter(AttendanceRecord.status.in_(["present", "late"])).count()
        rate = round(present / total * 100, 1) if total > 0 else 0
        result.append(TrendItem(date=d.strftime("%m-%d"), rate=rate))
    return result


# ==========================================
# 今日排课（下拉框）
# ==========================================

@router.get("/schedules_today", response_model=List[ScheduleBrief])
async def schedules_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today_weekday = date.today().isoweekday()  # 1=Mon
    q = db.query(CourseSchedule).filter(CourseSchedule.weekday == today_weekday)

    if current_user.role == "teacher":
        my_course_ids = [c.id for c in db.query(Course.id).filter(Course.teacher_id == current_user.id).all()]
        q = q.filter(CourseSchedule.course_id.in_(my_course_ids)) if my_course_ids else q.filter(False)

    schedules = q.all()
    return [
        ScheduleBrief(
            id=s.id,
            label=f"{s.course.name} - {s.class_.name} ({s.start_time.strftime('%H:%M')}~{s.end_time.strftime('%H:%M')})",
        )
        for s in schedules
    ]


# ==========================================
# 实时考勤记录（右侧时间线）
# ==========================================

@router.get("/recent", response_model=List[RecentActivity])
async def dashboard_recent(
    schedule_id: int = Query(..., description="排课ID"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    records = (
        db.query(AttendanceRecord)
        .filter(
            AttendanceRecord.schedule_id == schedule_id,
            AttendanceRecord.check_in_time.between(today_start, today_end),
        )
        .order_by(AttendanceRecord.check_in_time.desc())
        .limit(50)
        .all()
    )
    result = []
    for r in records:
        sf = db.query(StudentFeature).filter(StudentFeature.id == r.student_feature_id).first()
        result.append(RecentActivity(
            student_name=sf.name if sf else "未知",
            status=r.status,
            check_in_time=r.check_in_time.strftime("%H:%M:%S") if r.check_in_time else None,
        ))
    return result
