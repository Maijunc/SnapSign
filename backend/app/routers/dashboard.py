# backend/app/routers/dashboard.py
# 数据大屏路由：统计卡片 / 出勤趋势 / 今日排课 / 实时考勤 / 各课出勤概览

from datetime import date, timedelta, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User, Course, CourseSchedule, AttendanceRecord, StudentFeature, Class,
)
from app.schemas import (
    DashboardStats, TrendItem, RecentActivity, ScheduleBrief,
    CourseAttendanceSummary,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/dashboard", tags=["数据大屏"])


# ---------- 内部工具函数 ----------

def _get_today_schedules(db: Session, current_user: User) -> list[CourseSchedule]:
    """获取当前用户今日的排课列表"""
    today = date.today()
    today_wd = today.isoweekday()
    q = db.query(CourseSchedule).filter(CourseSchedule.weekday == today_wd)

    if current_user.role == "teacher":
        my_course_ids = [c.id for c in db.query(Course.id).filter(Course.teacher_id == current_user.id).all()]
        q = q.filter(CourseSchedule.course_id.in_(my_course_ids)) if my_course_ids else q.filter(False)

    # 过滤在有效周数范围内的排课
    schedules = []
    for s in q.all():
        if s.start_date and s.total_weeks:
            end_date = s.start_date + timedelta(weeks=s.total_weeks)
            if today < s.start_date or today >= end_date:
                continue
        schedules.append(s)
    return schedules


def _schedule_expected_total(schedule: CourseSchedule) -> int:
    return len(schedule.resolved_students)


def _schedule_class_name(schedule: CourseSchedule) -> str:
    return schedule.resolved_class_name or ""


# ==========================================
# 统计卡片（4 个指标 + 出勤率）
# ==========================================

@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    schedule_id: Optional[int] = Query(None, description="可选：按排课统计"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    today_schedules = _get_today_schedules(db, current_user)

    if schedule_id is not None:
        target_schedule = next((s for s in today_schedules if s.id == schedule_id), None)
        if not target_schedule:
            raise HTTPException(status_code=404, detail="今日排课不存在")

        expected_total = _schedule_expected_total(target_schedule)
        today_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.schedule_id == target_schedule.id,
            AttendanceRecord.check_in_time.between(today_start, today_end),
        ).all()

        present_count = sum(1 for r in today_records if r.status == "present")
        late_count = sum(1 for r in today_records if r.status == "late")
        signed_in = present_count + late_count
        absent_count = max(0, expected_total - signed_in)
        attendance_rate = round(signed_in / expected_total * 100, 1) if expected_total > 0 else None

        return DashboardStats(
            card1_title="当前课次应到",
            card1_value=expected_total,
            card2_title="当前课次已签到",
            card2_value=signed_in,
            card3_title="当前课次迟到",
            card3_value=late_count,
            card4_title="当前课次缺勤",
            card4_value=absent_count,
            attendance_rate=attendance_rate,
        )

    if current_user.role == "admin":
        # admin: 卡片按“今日排课应到/实到/迟到/缺勤”口径统计，
        # 并保留“学生档案总数”作为全局规模指标。
        card1_title = "学生档案总数"
        card1_value = db.query(func.count(StudentFeature.id)).scalar() or 0
        schedule_ids = [s.id for s in today_schedules]
        expected_total = sum(_schedule_expected_total(s) for s in today_schedules)

        today_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.schedule_id.in_(schedule_ids),
            AttendanceRecord.check_in_time.between(today_start, today_end),
        ).all() if schedule_ids else []

        present_count = sum(1 for r in today_records if r.status == "present")
        late_count = sum(1 for r in today_records if r.status == "late")
        signed_in = present_count + late_count
        absent_count = max(0, expected_total - signed_in)
        attendance_rate = round(signed_in / expected_total * 100, 1) if expected_total > 0 else None
    else:
        # teacher: 基于"应到人数"重新计算
        # 应到人数 = 各排课对应班级的学生数之和
        expected_total = 0
        my_schedule_ids = []
        for s in today_schedules:
            expected_total += _schedule_expected_total(s)
            my_schedule_ids.append(s.id)

        card1_title = "今日应到"
        card1_value = expected_total

        today_records = db.query(AttendanceRecord).filter(
            AttendanceRecord.schedule_id.in_(my_schedule_ids),
            AttendanceRecord.check_in_time.between(today_start, today_end),
        ).all() if my_schedule_ids else []

        present_count = sum(1 for r in today_records if r.status == "present")
        late_count = sum(1 for r in today_records if r.status == "late")
        # 缺勤 = 应到 - 已签到（不再依赖 absent 记录）
        signed_in = present_count + late_count
        absent_count = max(0, expected_total - signed_in)
        attendance_rate = round(signed_in / expected_total * 100, 1) if expected_total > 0 else None

    return DashboardStats(
        card1_title=card1_title,
        card1_value=card1_value,
        card2_title="今日已签到人次",
        card2_value=present_count + late_count,
        card3_title="今日迟到人次",
        card3_value=late_count,
        card4_title="今日缺勤人次",
        card4_value=absent_count,
        attendance_rate=attendance_rate,
    )


# ==========================================
# 今日各课出勤概览（教师大屏）
# ==========================================

@router.get("/course_attendance", response_model=List[CourseAttendanceSummary])
async def course_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    today_schedules = _get_today_schedules(db, current_user)
    result = []
    for s in today_schedules:
        expected = _schedule_expected_total(s)
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.schedule_id == s.id,
            AttendanceRecord.check_in_time.between(today_start, today_end),
        ).all()
        present = sum(1 for r in records if r.status == "present")
        late = sum(1 for r in records if r.status == "late")
        signed_in = present + late
        absent = max(0, expected - signed_in)
        rate = round(signed_in / expected * 100, 1) if expected > 0 else 0

        result.append(CourseAttendanceSummary(
            schedule_id=s.id,
            course_name=s.course.name if s.course else "",
            class_name=_schedule_class_name(s),
            time_range=f"{s.start_time.strftime('%H:%M')}-{s.end_time.strftime('%H:%M')}",
            expected=expected,
            present=present,
            late=late,
            absent=absent,
            rate=rate,
        ))
    return result


# ==========================================
# 近 7 日出勤率趋势（支持课程筛选）
# ==========================================

@router.get("/trend", response_model=List[TrendItem])
async def dashboard_trend(
    course_id: Optional[int] = Query(None, description="可选：按课程筛选趋势"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 确定可见的 schedule_ids
    if current_user.role == "teacher":
        my_course_ids = [c.id for c in db.query(Course.id).filter(Course.teacher_id == current_user.id).all()]
        my_sched_ids = [
            s.id for s in db.query(CourseSchedule.id).filter(CourseSchedule.course_id.in_(my_course_ids)).all()
        ] if my_course_ids else []
    else:
        my_sched_ids = None  # admin: 不限

    # 课程筛选
    if course_id is not None:
        course_sched_ids = [
            s.id for s in db.query(CourseSchedule.id).filter(CourseSchedule.course_id == course_id).all()
        ]
        if my_sched_ids is not None:
            course_sched_ids = [sid for sid in course_sched_ids if sid in my_sched_ids]
        my_sched_ids = course_sched_ids

    result = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        day_start = datetime.combine(d, datetime.min.time())
        day_end = datetime.combine(d, datetime.max.time())

        q = db.query(AttendanceRecord).filter(
            AttendanceRecord.check_in_time.between(day_start, day_end)
        )
        if my_sched_ids is not None:
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
    today_schedules = _get_today_schedules(db, current_user)
    return [
        ScheduleBrief(
            id=s.id,
            label=f"{s.course.name} - {_schedule_class_name(s)} ({s.start_time.strftime('%H:%M')}~{s.end_time.strftime('%H:%M')})",
        )
        for s in today_schedules
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


# ==========================================
# 学生端统计概览
# ==========================================

@router.get("/student_stats")
async def student_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """学生个人考勤统计概览"""
    sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    if not sf:
        return {
            "total_records": 0,
            "present_count": 0,
            "late_count": 0,
            "absent_count": 0,
            "attendance_rate": None,
            "course_stats": [],
        }

    # 总考勤统计
    all_records = db.query(AttendanceRecord).filter(
        AttendanceRecord.student_feature_id == sf.id
    ).all()

    present_count = sum(1 for r in all_records if r.status == "present")
    late_count = sum(1 for r in all_records if r.status == "late")
    absent_count = sum(1 for r in all_records if r.status == "absent")
    total = len(all_records)
    signed_in = present_count + late_count
    rate = round(signed_in / total * 100, 1) if total > 0 else None

    # 按课程分组统计
    course_map: dict[int, dict] = {}
    for r in all_records:
        schedule = r.schedule
        if not schedule:
            continue
        course_id = schedule.course_id
        if course_id not in course_map:
            course_map[course_id] = {
                "course_name": schedule.course.name if schedule.course else "未知",
                "present": 0, "late": 0, "absent": 0, "total": 0,
            }
        course_map[course_id]["total"] += 1
        if r.status == "present":
            course_map[course_id]["present"] += 1
        elif r.status == "late":
            course_map[course_id]["late"] += 1
        elif r.status == "absent":
            course_map[course_id]["absent"] += 1

    course_stats = []
    for cid, info in course_map.items():
        s = info["present"] + info["late"]
        course_stats.append({
            "course_name": info["course_name"],
            "present": info["present"],
            "late": info["late"],
            "absent": info["absent"],
            "total": info["total"],
            "rate": round(s / info["total"] * 100, 1) if info["total"] > 0 else 0,
        })

    return {
        "total_records": total,
        "present_count": present_count,
        "late_count": late_count,
        "absent_count": absent_count,
        "attendance_rate": rate,
        "course_stats": course_stats,
    }
