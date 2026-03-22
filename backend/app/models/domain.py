# backend/app/models/domain.py
from sqlalchemy import Column, Integer, String, Enum, LargeBinary, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Student(Base):
    """学生基础信息表"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="学生ID")
    student_number = Column(String(20), unique=True, index=True, nullable=False, comment="学号")
    name = Column(String(50), nullable=False, comment="姓名")
    gender = Column(Enum('M', 'F', 'Other'), comment="性别")
    
    # 建立与人脸特征表的一对一/一对多关系
    faces = relationship("FaceFeature", back_populates="student", cascade="all, delete-orphan")

class FaceFeature(Base):
    """人脸特征向量表"""
    __tablename__ = "face_features"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="特征ID")
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, comment="关联的学生ID")
    
    # LargeBinary (对应数据库的 BLOB)，用来存 OpenCV/dlib 提取出来的 128维 浮点数特征数组
    encoding_blob = Column(LargeBinary, nullable=False, comment="序列化后的特征向量")
    
    created_at = Column(DateTime, default=func.now(), comment="采集时间")

    # 建立反向关联
    student = relationship("Student", back_populates="faces")