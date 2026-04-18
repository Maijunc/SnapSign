# backend/app/models.py
# 统一的 SQLAlchemy ORM 模型定义

from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey, DateTime, Enum, Float, Table, Time, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ==========================================
# 多对多中间表：课程 ↔ 班级
# ==========================================
course_classes = Table(
    "course_classes",
    Base.metadata,
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
    Column("class_id", Integer, ForeignKey("classes.id"), primary_key=True),
)


# ==========================================
# 多对多中间表：班级 ↔ 学生（人脸特征）
# ==========================================
class_students = Table(
    "class_students",
    Base.metadata,
    Column("class_id", Integer, ForeignKey("classes.id"), primary_key=True),
    Column("student_feature_id", Integer, ForeignKey("student_features.id"), primary_key=True),
)


# ==========================================
# 用户与权限
# ==========================================

class User(Base):
    """系统用户表（学生/教师/管理员统一登录）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="登录账号")
    hashed_password = Column(String(128), nullable=False, comment="bcrypt 加盐哈希")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    role = Column(
        Enum("student", "teacher", "admin", name="user_role"),
        nullable=False,
        default="student",
        comment="角色：student / teacher / admin",
    )
    is_active = Column(Integer, default=1, comment="是否启用 1=是 0=否")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关联：教师拥有的课程
    courses = relationship("Course", back_populates="teacher")


# ==========================================
# 班级
# ==========================================

class Class(Base):
    """班级表"""
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="班级名称，如 计科2301班")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    courses = relationship("Course", secondary=course_classes, back_populates="classes")
    schedules = relationship("CourseSchedule", back_populates="class_")
    students = relationship("StudentFeature", secondary=class_students, back_populates="classes")


# ==========================================
# 课程
# ==========================================

class Course(Base):
    """课程表"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="课程名称，如 高等数学")
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="授课教师")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    teacher = relationship("User", back_populates="courses")
    classes = relationship("Class", secondary=course_classes, back_populates="courses")
    schedules = relationship("CourseSchedule", back_populates="course")


# ==========================================
# 排课（某课程在某班级的具体上课时间段）
# ==========================================

class CourseSchedule(Base):
    """排课表"""
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, comment="关联课程")
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False, comment="关联班级")
    weekday = Column(Integer, nullable=False, comment="星期几 1=周一 ... 7=周日")
    start_date = Column(Date, nullable=False, comment="首次上课日期")
    total_weeks = Column(Integer, nullable=False, default=16, comment="持续周数")
    start_time = Column(Time, nullable=False, comment="上课时间")
    end_time = Column(Time, nullable=False, comment="下课时间")
    location = Column(String(100), comment="上课地点，如 教学楼A-301")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    course = relationship("Course", back_populates="schedules")
    class_ = relationship("Class", back_populates="schedules")
    attendance_records = relationship("AttendanceRecord", back_populates="schedule")


# ==========================================
# 考勤记录（每次签到一条）
# ==========================================

class AttendanceRecord(Base):
    """考勤记录表"""
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    schedule_id = Column(Integer, ForeignKey("course_schedules.id"), nullable=False, comment="关联排课")
    student_feature_id = Column(Integer, ForeignKey("student_features.id"), nullable=False, comment="关联学生特征")
    student_name = Column(String(50), comment="冗余存储学生姓名，方便查询")
    check_in_time = Column(DateTime, default=func.now(), comment="签到时间")
    status = Column(
        Enum("present", "late", "absent", name="attendance_status"),
        nullable=False,
        default="present",
        comment="考勤状态",
    )
    face_distance = Column(Float, comment="人脸匹配距离，越小越像")
    created_at = Column(DateTime, default=func.now(), comment="记录创建时间")

    schedule = relationship("CourseSchedule", back_populates="attendance_records")
    student_feature = relationship("StudentFeature")


# ==========================================
# 当前正在使用的模型（与现有前端完全兼容）
# ==========================================

class StudentFeature(Base):
    """学生人脸特征表（录入+比对都依赖这张表）"""
    __tablename__ = "student_features"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, index=True, comment="学号")
    name = Column(String(50), comment="姓名")
    face_encoding = Column(LargeBinary, comment="128维人脸特征向量(BLOB)")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="关联系统用户")

    user = relationship("User")
    classes = relationship("Class", secondary=class_students, back_populates="students")


# ==========================================
# 节假日表
# ==========================================

class Holiday(Base):
    """节假日表（排课中标注放假日期）"""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    holiday_date = Column(Date, unique=True, nullable=False, index=True, comment="放假日期")
    name = Column(String(50), nullable=False, comment="节假日名称，如 国庆节")


# ==========================================
# 预留模型（后续扩展三端功能时启用）
# ==========================================

class Student(Base):
    """学生基础信息表"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_number = Column(String(20), unique=True, index=True, nullable=False, comment="学号")
    name = Column(String(50), nullable=False, comment="姓名")
    gender = Column(Enum('M', 'F', 'Other'), comment="性别")

    faces = relationship("FaceFeature", back_populates="student", cascade="all, delete-orphan")


class FaceFeature(Base):
    """人脸特征向量表（支持一人多次采集）"""
    __tablename__ = "face_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, comment="关联学生ID")
    encoding_blob = Column(LargeBinary, nullable=False, comment="序列化后的特征向量")
    created_at = Column(DateTime, default=func.now(), comment="采集时间")

    student = relationship("Student", back_populates="faces")
