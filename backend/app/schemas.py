# backend/app/schemas.py
# 统一的 Pydantic 请求/响应模型（前后端数据契约）

from datetime import time, datetime, date
from typing import Optional, List
from pydantic import BaseModel


# ==========================================
# 认证相关
# ==========================================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功后返回的 Token"""
    access_token: str
    token_type: str = "bearer"
    role: str
    real_name: str


# ==========================================
# 人脸相关
# ==========================================

class FaceRegisterRequest(BaseModel):
    """人脸录入请求"""
    student_id: str
    name: str
    image_base64: str


class FaceCheckRequest(BaseModel):
    """考勤打卡请求（必须绑定排课）"""
    image_base64: str
    schedule_id: int


# ==========================================
# 班级相关
# ==========================================

class ClassCreate(BaseModel):
    name: str

class ClassOut(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


# ==========================================
# 课程相关
# ==========================================

class CourseCreate(BaseModel):
    name: str
    teacher_id: int
    class_ids: List[int] = []

class CourseOut(BaseModel):
    id: int
    name: str
    teacher_id: int
    teacher_name: Optional[str] = None
    classes: List[ClassOut] = []
    model_config = {"from_attributes": True}


# ==========================================
# 排课相关
# ==========================================

class ScheduleCreate(BaseModel):
    course_id: int
    class_id: int
    start_date: date    # 首次上课日期，weekday 自动推算
    total_weeks: int = 16
    start_time: time
    end_time: time
    location: str = ""

class ScheduleOut(BaseModel):
    id: int
    course_id: int
    class_id: int
    course_name: Optional[str] = None
    class_name: Optional[str] = None
    weekday: int
    start_date: Optional[date] = None
    total_weeks: Optional[int] = None
    start_time: time
    end_time: time
    location: Optional[str] = None
    model_config = {"from_attributes": True}

class ScheduleWeekOut(BaseModel):
    """排课的某一周信息"""
    week: int
    date: date
    is_holiday: bool = False
    holiday_name: Optional[str] = None


# ==========================================
# 考勤记录相关
# ==========================================

class AttendanceRecordOut(BaseModel):
    id: int
    schedule_id: int
    student_feature_id: int
    student_name: Optional[str] = None
    check_in_time: Optional[datetime] = None
    status: str
    face_distance: Optional[float] = None
    model_config = {"from_attributes": True}


# ==========================================
# 用户管理相关（管理员 CRUD）
# ==========================================

class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    role: str = "student"

class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[int] = None

class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    is_active: int
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ==========================================
# 学生考勤自查（包含课程名称等冗余信息）
# ==========================================

class MyAttendanceOut(BaseModel):
    id: int
    schedule_id: int
    course_name: Optional[str] = None
    class_name: Optional[str] = None
    check_in_time: Optional[datetime] = None
    status: str
    face_distance: Optional[float] = None
    model_config = {"from_attributes": True}


# ==========================================
# 节假日相关
# ==========================================

class HolidayCreate(BaseModel):
    holiday_date: date
    name: str

class HolidayOut(BaseModel):
    id: int
    holiday_date: date
    name: str
    model_config = {"from_attributes": True}


# ==========================================
# 班级学生管理
# ==========================================

class ClassStudentsAdd(BaseModel):
    """批量添加学生到班级"""
    student_feature_ids: List[int]

class StudentFeatureOut(BaseModel):
    id: int
    student_id: str
    name: Optional[str] = None
    model_config = {"from_attributes": True}


# ==========================================
# 数据大屏
# ==========================================

class DashboardStats(BaseModel):
    card1_title: str
    card1_value: int
    card2_title: str = "今日已签到"
    card2_value: int = 0
    card3_title: str = "今日迟到"
    card3_value: int = 0
    card4_title: str = "今日缺勤"
    card4_value: int = 0

class TrendItem(BaseModel):
    date: str
    rate: float

class RecentActivity(BaseModel):
    student_name: str
    status: str
    check_in_time: Optional[str] = None

class ScheduleBrief(BaseModel):
    """排课简要（下拉框使用）"""
    id: int
    label: str


# ==========================================
# 教学日历
# ==========================================

class CalendarEvent(BaseModel):
    """日历上某天的一节课"""
    schedule_id: int
    course_name: str
    class_name: str
    start_time: str       # "08:00"
    end_time: str         # "09:40"
    location: Optional[str] = None
    is_holiday: bool = False
    holiday_name: Optional[str] = None

class CalendarDayOut(BaseModel):
    """某天的所有课程事件"""
    date: date
    events: List[CalendarEvent] = []
