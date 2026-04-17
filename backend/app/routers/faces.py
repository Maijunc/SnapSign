# backend/app/routers/faces.py
# 人脸录入 & 考勤打卡路由

import base64
from datetime import datetime, timezone
import numpy as np
import cv2
import face_recognition

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentFeature, CourseSchedule, AttendanceRecord
from app.schemas import FaceRegisterRequest, FaceCheckRequest

router = APIRouter(prefix="/api/v1/faces", tags=["人脸识别"])


# ==========================================
# 人脸录入（视觉大脑）
# ==========================================
@router.post("/register")
async def register_face(data: FaceRegisterRequest, db: Session = Depends(get_db)):
    try:
        # 步骤 A：图片解码
        encoded_data = data.image_base64.split(",")[1] if "," in data.image_base64 else data.image_base64
        img_data = base64.b64decode(encoded_data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # 步骤 B：特征提取
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_img)
        if not face_locations:
            raise HTTPException(status_code=400, detail="照片中未检测到人脸，请正对摄像头！")
        if len(face_locations) > 1:
            raise HTTPException(status_code=400, detail="检测到多张人脸，请确保画面中只有你一个人！")

        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        feature_vector = face_encodings[0]

        # 步骤 C：数据持久化
        existing_student = db.query(StudentFeature).filter(StudentFeature.student_id == data.student_id).first()
        if existing_student:
            raise HTTPException(status_code=400, detail="该学号已存在，请勿重复录入！")

        feature_blob = feature_vector.tobytes()
        new_student = StudentFeature(
            student_id=data.student_id,
            name=data.name,
            face_encoding=feature_blob
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)

        print(f"🎉 成功录入！{data.name} 的 128 维特征已序列化并存入数据库！")
        return {
            "status": "success",
            "message": f"成功提取 {data.name} 的面部特征并存入数据库！"
        }

    except HTTPException:
        raise
    except Exception as e:
        print("❌ 后端发生错误:", str(e))
        raise HTTPException(status_code=500, detail="服务器特征提取失败，请检查控制台日志。")


# ==========================================
# 考勤打卡（记忆检索 + 考勤落库）
# ==========================================
@router.post("/check_in")
async def check_in_face(data: FaceCheckRequest, db: Session = Depends(get_db)):
    try:
        # 步骤 0：校验排课是否存在
        schedule = db.query(CourseSchedule).filter(CourseSchedule.id == data.schedule_id).first()
        if not schedule:
            raise HTTPException(status_code=400, detail="排课不存在，请从课程页面进入打卡！")

        # 步骤 A：图片解码与特征提取
        encoded_data = data.image_base64.split(",")[1] if "," in data.image_base64 else data.image_base64
        img_data = base64.b64decode(encoded_data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_img)
        if not face_locations:
            raise HTTPException(status_code=400, detail="未检测到人脸，请正对摄像头！")

        unknown_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]

        # 步骤 B：从数据库拉取所有已注册的记忆
        all_students = db.query(StudentFeature).all()
        if not all_students:
            raise HTTPException(status_code=400, detail="系统未录入任何学生档案！")

        known_encodings = [np.frombuffer(s.face_encoding, dtype=np.float64) for s in all_students]

        # 步骤 C：计算欧氏距离
        distances = face_recognition.face_distance(known_encodings, unknown_encoding)
        best_match_index = np.argmin(distances)
        min_distance = distances[best_match_index]

        # 步骤 D：阈值判定
        THRESHOLD = 0.45
        if min_distance <= THRESHOLD:
            matched_student = all_students[best_match_index]

            # 步骤 E：检查是否重复签到
            existing = (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.schedule_id == data.schedule_id,
                    AttendanceRecord.student_feature_id == matched_student.id,
                )
                .first()
            )
            if existing:
                return {
                    "status": "duplicate",
                    "message": f"{matched_student.name} 已签到过，无需重复打卡",
                    "student_name": matched_student.name,
                    "distance": float(min_distance),
                }

            # 步骤 F：判定迟到（超过上课时间15分钟算迟到）
            now = datetime.now()
            scheduled_start = datetime.combine(now.date(), schedule.start_time)
            if now > scheduled_start.replace(minute=scheduled_start.minute + 15):
                status = "late"
            else:
                status = "present"

            # 步骤 G：写入考勤记录
            record = AttendanceRecord(
                schedule_id=data.schedule_id,
                student_feature_id=matched_student.id,
                student_name=matched_student.name,
                check_in_time=now,
                status=status,
                face_distance=float(min_distance),
            )
            db.add(record)
            db.commit()

            status_text = "签到成功" if status == "present" else "迟到签到"
            print(f"✅ {status_text}！识别为: {matched_student.name} (差异度: {min_distance:.3f})")
            return {
                "status": "success",
                "message": f"{status_text}！欢迎你，{matched_student.name}",
                "student_name": matched_student.name,
                "distance": float(min_distance),
                "attendance_status": status,
            }
        else:
            print(f"❌ 考勤失败！最小差异度: {min_distance:.3f}。陌生人拦截机制已触发。")
            return {
                "status": "fail",
                "message": "未匹配到档案，请确认是否已录入人脸！"
            }

    except HTTPException:
        raise
    except Exception as e:
        print("❌ 考勤接口报错:", str(e))
        raise HTTPException(status_code=500, detail="服务器比对失败。")
