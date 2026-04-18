# backend/scripts/seed_test_data.py
"""
一键生成测试数据脚本
用法：cd backend && conda activate snapsign && python -m scripts.seed_test_data

生成内容：
  - 20 个学生账号 (student01 ~ student20)
  - 20 条学生人脸特征（随机向量模拟，不影响结构）
  - 学生分配到班级
  - 近 7 天的考勤记录（模拟真实出勤/迟到/缺勤分布）
"""

import sys, os, random
from datetime import datetime, date, timedelta, time

import numpy as np

# 让 import app.xxx 能正常工作
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models import (
    User, StudentFeature, Class, Course, CourseSchedule,
    AttendanceRecord,
)
from app.auth import hash_password

# ==========================================
# 配置区
# ==========================================
STUDENT_COUNT = 20
DAYS_BACK = 7                  # 往前补几天的考勤（不含今天）
PRESENT_RATIO = 0.75
LATE_RATIO = 0.10              # 剩余 15% 为缺勤

STUDENT_NAMES = [
    "王明", "李华", "张伟", "刘洋", "陈静",
    "杨帆", "赵磊", "黄晓", "周婷", "吴杰",
    "孙悦", "马超", "朱丹", "胡勇", "林婉",
    "何亮", "郭雨", "罗敏", "宋杰", "谢瑶",
]


def main():
    db = SessionLocal()
    try:
        # ========== 1. 创建学生账号 ==========
        print("👤 创建学生账号...")
        student_users = []
        for i in range(1, STUDENT_COUNT + 1):
            uname = f"student{i:02d}"
            user = db.query(User).filter(User.username == uname).first()
            if not user:
                user = User(
                    username=uname,
                    hashed_password=hash_password("student123"),
                    real_name=STUDENT_NAMES[i - 1] if i <= len(STUDENT_NAMES) else f"学生{i}",
                    role="student",
                )
                db.add(user)
                db.flush()
            student_users.append(user)
        db.commit()
        print(f"   ✅ {len(student_users)} 个学生账号就绪")

        # ========== 2. 创建人脸特征 ==========
        print("🧑 创建人脸特征...")
        features = []
        for i, user in enumerate(student_users):
            sid = f"2023{i + 1:04d}"
            sf = db.query(StudentFeature).filter(StudentFeature.student_id == sid).first()
            if not sf:
                fake_encoding = np.random.randn(128).astype(np.float64).tobytes()
                sf = StudentFeature(
                    student_id=sid,
                    name=user.real_name,
                    face_encoding=fake_encoding,
                    user_id=user.id,
                )
                db.add(sf)
                db.flush()
            features.append(sf)
        db.commit()
        print(f"   ✅ {len(features)} 条人脸特征就绪")

        # ========== 3. 分配学生到班级 ==========
        print("📋 分配学生到班级...")
        classes = db.query(Class).order_by(Class.id).all()
        if len(classes) < 2:
            print("   ⚠️ 班级不足 2 个，跳过分配")
        else:
            c1, c2 = classes[0], classes[1]
            for sf in features[:12]:
                if sf not in c1.students:
                    c1.students.append(sf)
            for sf in features[12:]:
                if sf not in c2.students:
                    c2.students.append(sf)
            db.commit()
            print(f"   ✅ {c1.name}: {len(c1.students)} 人, {c2.name}: {len(c2.students)} 人")

        # ========== 4. 生成考勤记录 ==========
        print("📊 生成考勤记录...")
        schedules = db.query(CourseSchedule).all()
        if not schedules:
            print("   ⚠️ 无排课数据，跳过考勤生成")
        else:
            record_count = 0
            today = date.today()

            for day_offset in range(DAYS_BACK, 0, -1):
                d = today - timedelta(days=day_offset)
                weekday_iso = d.isoweekday()

                day_schedules = [s for s in schedules if s.weekday == weekday_iso]
                if not day_schedules:
                    continue

                for sched in day_schedules:
                    cls = db.query(Class).filter(Class.id == sched.class_id).first()
                    if not cls or not cls.students:
                        continue

                    for sf in cls.students:
                        existing = db.query(AttendanceRecord).filter(
                            AttendanceRecord.schedule_id == sched.id,
                            AttendanceRecord.student_feature_id == sf.id,
                            AttendanceRecord.check_in_time >= datetime.combine(d, time(0, 0)),
                            AttendanceRecord.check_in_time < datetime.combine(d + timedelta(days=1), time(0, 0)),
                        ).first()
                        if existing:
                            continue

                        roll = random.random()
                        if roll < PRESENT_RATIO:
                            status = "present"
                            minutes_early = random.randint(0, 5)
                            check_time = datetime.combine(d, sched.start_time) - timedelta(minutes=minutes_early)
                            distance = round(random.uniform(0.20, 0.40), 4)
                        elif roll < PRESENT_RATIO + LATE_RATIO:
                            status = "late"
                            minutes_late = random.randint(1, 15)
                            check_time = datetime.combine(d, sched.start_time) + timedelta(minutes=minutes_late)
                            distance = round(random.uniform(0.25, 0.42), 4)
                        else:
                            status = "absent"
                            check_time = None
                            distance = None

                        record = AttendanceRecord(
                            schedule_id=sched.id,
                            student_feature_id=sf.id,
                            student_name=sf.name,
                            check_in_time=check_time,
                            status=status,
                            face_distance=distance,
                        )
                        db.add(record)
                        record_count += 1

                db.commit()

            print(f"   ✅ 共生成 {record_count} 条考勤记录")

        # ========== 5. 汇总 ==========
        print()
        print("=" * 45)
        print("🎉 测试数据生成完毕！")
        print(f"   用户总数:     {db.query(User).count()}")
        print(f"   人脸特征:     {db.query(StudentFeature).count()}")
        print(f"   班级数:       {db.query(Class).count()}")
        print(f"   排课数:       {db.query(CourseSchedule).count()}")
        print(f"   考勤记录:     {db.query(AttendanceRecord).count()}")
        print("=" * 45)
        print()
        print("📌 测试账号一览：")
        print("   管理员:  admin / admin123")
        print("   教师:    teacher01 / teacher123")
        print("   学生:    student01~student20 / student123")

    finally:
        db.close()


if __name__ == "__main__":
    main()
