# backend/app/main.py
# SnapSign 后端入口：只负责组装，不写业务逻辑

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from datetime import time, date

from app.database import engine, Base, SessionLocal
from app.routers import faces, admin, auth, courses, dashboard
from app.models import User, Class, Course, CourseSchedule, Holiday
from app.auth import hash_password

# 导入 models 模块，确保 SQLAlchemy 感知到所有表定义
import app.models  # noqa: F401

# ==========================================
# 启动时自动建表
# ==========================================
Base.metadata.create_all(bind=engine)

# ==========================================
# 创建默认种子账号（首次运行时写入）
# ==========================================
def _seed_default_users():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", hashed_password=hash_password("admin123"), real_name="系统管理员", role="admin"))
        if not db.query(User).filter(User.username == "teacher01").first():
            db.add(User(username="teacher01", hashed_password=hash_password("teacher123"), real_name="张老师", role="teacher"))
        if not db.query(User).filter(User.username == "student01").first():
            db.add(User(username="student01", hashed_password=hash_password("student123"), real_name="李同学", role="student"))
        db.commit()
    finally:
        db.close()


def _seed_course_data():
    """首次运行时创建示例班级、课程和排课"""
    db = SessionLocal()
    try:
        # 跳过：如果已有班级数据则不再重复插入
        if db.query(Class).first():
            return

        # 创建示例班级
        c1 = Class(name="计科2301班")
        c2 = Class(name="计科2302班")
        db.add_all([c1, c2])
        db.flush()  # 拿到 id

        # 查出教师（种子用户 teacher01）
        teacher = db.query(User).filter(User.username == "teacher01").first()
        if not teacher:
            return

        # 创建示例课程并关联班级
        course1 = Course(name="高等数学", teacher_id=teacher.id, classes=[c1, c2])
        course2 = Course(name="Python程序设计", teacher_id=teacher.id, classes=[c1])
        db.add_all([course1, course2])
        db.flush()

        # 创建示例排课（start_date 取下周一起的对应日期）
        import datetime as _dt
        _today = _dt.date.today()
        _next_monday = _today + _dt.timedelta(days=(7 - _today.weekday()) % 7 or 7)
        _next_tuesday = _next_monday + _dt.timedelta(days=1)
        _next_wednesday = _next_monday + _dt.timedelta(days=2)

        db.add_all([
            CourseSchedule(course_id=course1.id, class_id=c1.id, weekday=1, start_date=_next_monday, total_weeks=16, start_time=time(8, 0), end_time=time(9, 40), location="教学楼A-301"),
            CourseSchedule(course_id=course1.id, class_id=c2.id, weekday=3, start_date=_next_wednesday, total_weeks=16, start_time=time(10, 0), end_time=time(11, 40), location="教学楼A-302"),
            CourseSchedule(course_id=course2.id, class_id=c1.id, weekday=2, start_date=_next_tuesday, total_weeks=16, start_time=time(14, 0), end_time=time(15, 40), location="实验楼B-201"),
        ])
        db.commit()
        print("📚 种子课程数据已写入！")
    finally:
        db.close()


def _seed_holidays():
    """写入示例节假日"""
    db = SessionLocal()
    try:
        if db.query(Holiday).first():
            return
        year = date.today().year
        holiday_seeds = {
            2026: [
                (1, 1, "元旦"), (1, 2, "元旦"), (1, 3, "元旦"),
                (2, 15, "春节"), (2, 16, "春节"), (2, 17, "春节"),
                (2, 18, "春节"), (2, 19, "春节"), (2, 20, "春节"),
                (2, 21, "春节"), (2, 22, "春节"), (2, 23, "春节"),
                (4, 4, "清明节"), (4, 5, "清明节"), (4, 6, "清明节"),
                (5, 1, "劳动节"), (5, 2, "劳动节"), (5, 3, "劳动节"),
                (5, 4, "劳动节"), (5, 5, "劳动节"),
                (6, 19, "端午节"), (6, 20, "端午节"), (6, 21, "端午节"),
                (9, 25, "中秋节"), (9, 26, "中秋节"), (9, 27, "中秋节"),
                (10, 1, "国庆节"), (10, 2, "国庆节"), (10, 3, "国庆节"),
                (10, 4, "国庆节"), (10, 5, "国庆节"), (10, 6, "国庆节"),
                (10, 7, "国庆节"),
            ],
        }
        seed_items = holiday_seeds.get(year, [
            (1, 1, "元旦"),
            (5, 1, "劳动节"),
            (10, 1, "国庆节"),
            (10, 2, "国庆节"),
            (10, 3, "国庆节"),
        ])
        db.add_all([
            Holiday(holiday_date=date(year, month, day), name=name)
            for month, day, name in seed_items
        ])
        db.commit()
        print("🎉 种子节假日数据已写入！")
    finally:
        db.close()


_seed_default_users()
_seed_course_data()
_seed_holidays()

# ==========================================
# FastAPI 应用初始化
# ==========================================
app = FastAPI(title="SnapSign API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 注册业务路由
# ==========================================
app.include_router(auth.router)
app.include_router(faces.router)
app.include_router(admin.router)
app.include_router(courses.router)
app.include_router(dashboard.router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)