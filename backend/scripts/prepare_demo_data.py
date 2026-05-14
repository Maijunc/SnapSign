"""
Prepare screenshot-friendly demo data for SnapSign.

Usage:
  cd backend
  python -m scripts.prepare_demo_data

What this script does:
1) Reuse seed_test_data to create students/features/history attendance.
2) Ensure there are schedules active today for teacher dashboard.
3) Generate mixed attendance records for today (present/late/absent).
4) Create sample appeals and leave requests for review pages.

The script is idempotent and safe to run multiple times.
"""

import os
import sys
import random
from datetime import date, datetime, timedelta, time

# Ensure backend root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models import (
    User,
    Class,
    Course,
    CourseSchedule,
    StudentFeature,
    AttendanceRecord,
    Appeal,
    LeaveRequest,
)
from app.auth import hash_password
from scripts.seed_test_data import main as seed_base_data


RANDOM_SEED = 20260420
PRESENT_RATIO = 0.70
LATE_RATIO = 0.15
# Remaining ratio => absent


def ensure_user(db, username: str, real_name: str, role: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user
    user = User(
        username=username,
        hashed_password=hash_password(password),
        real_name=real_name,
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def ensure_active_schedules(db):
    """Make sure at least two schedules are active today for screenshots."""
    today = date.today()
    today_wd = today.isoweekday()

    teacher = db.query(User).filter(User.username == "teacher01").first()
    if not teacher:
        teacher = ensure_user(db, "teacher01", "张老师", "teacher", "teacher123")

    classes = db.query(Class).order_by(Class.id).all()
    if not classes:
        c1 = Class(name="计科2301班")
        c2 = Class(name="计科2302班")
        db.add_all([c1, c2])
        db.flush()
        classes = [c1, c2]

    courses = db.query(Course).filter(Course.teacher_id == teacher.id).order_by(Course.id).all()
    if not courses:
        course1 = Course(name="高等数学", teacher_id=teacher.id, classes=[classes[0]])
        db.add(course1)
        db.flush()
        courses = [course1]

    # Force at least 2 active schedules today for dashboard screenshots.
    schedule_templates = [
        (courses[0], classes[0], time(8, 0), time(9, 40), "教学楼A-301"),
    ]
    if len(classes) > 1:
        second_course = courses[1] if len(courses) > 1 else courses[0]
        schedule_templates.append((second_course, classes[1], time(10, 0), time(11, 40), "教学楼A-302"))

    active_start = today - timedelta(weeks=3)

    created = 0
    updated = 0
    schedule_ids = []

    for course, cls, st, et, location in schedule_templates:
        schedule = (
            db.query(CourseSchedule)
            .filter(
                CourseSchedule.course_id == course.id,
                CourseSchedule.class_id == cls.id,
                CourseSchedule.weekday == today_wd,
            )
            .first()
        )

        if schedule:
            # Keep it active today.
            if schedule.start_date > today or (schedule.start_date + timedelta(weeks=schedule.total_weeks)) <= today:
                schedule.start_date = active_start
                schedule.total_weeks = max(schedule.total_weeks, 16)
                updated += 1
            schedule_ids.append(schedule.id)
            continue

        schedule = CourseSchedule(
            course_id=course.id,
            class_id=cls.id,
            weekday=today_wd,
            start_date=active_start,
            total_weeks=16,
            start_time=st,
            end_time=et,
            location=location,
        )
        db.add(schedule)
        db.flush()
        created += 1
        schedule_ids.append(schedule.id)

    db.commit()
    return schedule_ids, created, updated


def ensure_students_in_classes(db):
    """Ensure each student belongs to at most one class in demo data."""
    classes = db.query(Class).order_by(Class.id).all()
    students = db.query(StudentFeature).order_by(StudentFeature.id).all()
    if len(classes) < 2 or len(students) < 10:
        return

    c1, c2 = classes[0], classes[1]

    # Step 1: global cleanup - each student keeps only one class membership.
    for sf in students:
        if len(sf.classes) <= 1:
            continue
        keep = sorted(sf.classes, key=lambda c: c.id)[0]
        for cls in list(sf.classes):
            if cls.id != keep.id:
                cls.students.remove(sf)

    # Step 2: make demo classes mutually exclusive and deterministic.
    target_c1_ids = {sf.id for sf in students[:12]}
    target_c2_ids = {sf.id for sf in students[12:24]}

    for sf in list(c1.students):
        if sf.id not in target_c1_ids:
            c1.students.remove(sf)
    for sf in list(c2.students):
        if sf.id not in target_c2_ids:
            c2.students.remove(sf)

    for sf in students[:12]:
        if sf not in c1.students:
            c1.students.append(sf)
        if sf in c2.students:
            c2.students.remove(sf)

    for sf in students[12:24]:
        if sf not in c2.students:
            c2.students.append(sf)
        if sf in c1.students:
            c1.students.remove(sf)

    db.commit()


def generate_today_attendance(db, schedule_ids):
    """Create clear mixed statuses for today's dashboard and list screenshots."""
    random.seed(RANDOM_SEED)
    today = date.today()

    # Remove records generated today for these schedules to keep run idempotent.
    existing = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.schedule_id.in_(schedule_ids))
        .all()
    )
    removable_ids = []
    for rec in existing:
        if rec.check_in_time and rec.check_in_time.date() == today:
            removable_ids.append(rec.id)
        elif rec.check_in_time is None and rec.created_at and rec.created_at.date() == today:
            removable_ids.append(rec.id)

    if removable_ids:
        db.query(Appeal).filter(Appeal.attendance_id.in_(removable_ids)).delete(synchronize_session=False)

    removed = 0
    for rec in existing:
        if rec.check_in_time and rec.check_in_time.date() == today:
            db.delete(rec)
            removed += 1
        elif rec.check_in_time is None and rec.created_at and rec.created_at.date() == today:
            db.delete(rec)
            removed += 1
    db.commit()

    created = 0
    status_counter = {"present": 0, "late": 0, "absent": 0}

    for sid in schedule_ids:
        schedule = db.query(CourseSchedule).filter(CourseSchedule.id == sid).first()
        if not schedule or not schedule.class_:
            continue
        class_students = list(schedule.class_.students)
        if not class_students:
            continue

        for idx, sf in enumerate(class_students):
            # Deterministic pattern per 10 students: 7 present, 2 late, 1 absent.
            slot = idx % 10
            if slot <= 6:
                status = "present"
                minute_offset = random.randint(0, 5)
                check_in_time = datetime.combine(today, schedule.start_time) - timedelta(minutes=minute_offset)
                face_distance = round(random.uniform(0.20, 0.39), 4)
            elif slot <= 8:
                status = "late"
                minute_offset = random.randint(1, 20)
                check_in_time = datetime.combine(today, schedule.start_time) + timedelta(minutes=minute_offset)
                face_distance = round(random.uniform(0.28, 0.44), 4)
            else:
                status = "absent"
                check_in_time = None
                face_distance = None

            record = AttendanceRecord(
                schedule_id=schedule.id,
                student_feature_id=sf.id,
                student_name=sf.name,
                check_in_time=check_in_time,
                status=status,
                face_distance=face_distance,
            )
            db.add(record)
            created += 1
            status_counter[status] += 1

    db.commit()
    return removed, created, status_counter


def seed_appeals_and_leaves(db, schedule_ids):
    """Create demo review data for teacher pages."""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Clean previous demo rows
    demo_appeals = db.query(Appeal).filter(Appeal.reason.like("[DEMO]%")).all()
    for row in demo_appeals:
        db.delete(row)
    demo_leaves = db.query(LeaveRequest).filter(LeaveRequest.reason.like("[DEMO]%")).all()
    for row in demo_leaves:
        db.delete(row)
    db.commit()

    # Appeals: take today's late/absent records
    records = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.schedule_id.in_(schedule_ids))
        .order_by(AttendanceRecord.id.desc())
        .all()
    )
    late_or_absent = [r for r in records if r.status in ("late", "absent")][:6]

    appeal_statuses = ["pending", "approved", "rejected", "pending", "approved", "rejected"]
    appeal_count = 0
    for idx, rec in enumerate(late_or_absent):
        sf = db.query(StudentFeature).filter(StudentFeature.id == rec.student_feature_id).first()
        if not sf or not sf.user_id:
            continue
        appeal = Appeal(
            attendance_id=rec.id,
            user_id=sf.user_id,
            reason=f"[DEMO] 课堂考勤异常申诉样例 {idx + 1}",
            status=appeal_statuses[idx],
            reply="样例审批回复" if appeal_statuses[idx] != "pending" else None,
        )
        db.add(appeal)
        appeal_count += 1

    # Leaves: 3 pending + 2 approved + 1 rejected
    schedules = [db.query(CourseSchedule).filter(CourseSchedule.id == sid).first() for sid in schedule_ids]
    schedules = [s for s in schedules if s]
    users = db.query(User).filter(User.role == "student").order_by(User.id).limit(8).all()

    leave_statuses = ["pending", "pending", "pending", "approved", "approved", "rejected"]
    leave_count = 0

    for idx, status in enumerate(leave_statuses):
        if idx >= len(users) or not schedules:
            break
        schedule = schedules[idx % len(schedules)]
        leave = LeaveRequest(
            user_id=users[idx].id,
            schedule_id=schedule.id,
            leave_date=tomorrow,
            reason=f"[DEMO] 请假申请样例 {idx + 1}",
            status=status,
            reply="样例审批回复" if status != "pending" else None,
        )
        db.add(leave)
        leave_count += 1

    db.commit()
    return appeal_count, leave_count


def main():
    print("[1/5] Seeding baseline users/features/history records...")
    seed_base_data()

    db = SessionLocal()
    try:
        print("[2/5] Ensuring classes have enough students...")
        ensure_students_in_classes(db)

        print("[3/5] Ensuring active schedules today...")
        schedule_ids, created_sched, updated_sched = ensure_active_schedules(db)

        print("[4/5] Generating mixed attendance for today...")
        removed, created_att, status_counter = generate_today_attendance(db, schedule_ids)

        print("[5/5] Seeding demo appeals and leave requests...")
        appeal_count, leave_count = seed_appeals_and_leaves(db, schedule_ids)

        total_users = db.query(User).count()
        total_students = db.query(StudentFeature).count()
        total_classes = db.query(Class).count()
        total_courses = db.query(Course).count()
        total_schedules = db.query(CourseSchedule).count()
        total_attendance = db.query(AttendanceRecord).count()

        print("\n=== DEMO DATA READY ===")
        print(f"Users: {total_users}")
        print(f"Student features: {total_students}")
        print(f"Classes: {total_classes}")
        print(f"Courses: {total_courses}")
        print(f"Schedules: {total_schedules} (today active target ids: {schedule_ids})")
        print(f"Attendance total: {total_attendance}")
        print(f"Today attendance recreated: removed={removed}, created={created_att}")
        print(
            "Today status mix: "
            f"present={status_counter['present']}, "
            f"late={status_counter['late']}, "
            f"absent={status_counter['absent']}"
        )
        print(f"Demo appeals inserted: {appeal_count}")
        print(f"Demo leaves inserted: {leave_count}")
        print("\nDemo accounts:")
        print("- admin / admin123")
        print("- teacher01 / teacher123")
        print("- student01~student20 / student123")

    finally:
        db.close()


if __name__ == "__main__":
    main()
