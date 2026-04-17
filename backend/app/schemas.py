# backend/app/schemas.py
# 统一的 Pydantic 请求/响应模型（前后端数据契约）

from datetime import time, datetime
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
    weekday: int        # 1=周一 ... 7=周日
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
    start_time: time
    end_time: time
    location: Optional[str] = None
    model_config = {"from_attributes": True}


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
