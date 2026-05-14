# backend/app/routers/faces.py
# 人脸录入 & 考勤打卡路由

import base64
from datetime import datetime, timedelta, timezone
import numpy as np
import cv2
import face_recognition

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudentFeature, CourseSchedule, AttendanceRecord, User, class_students
from app.schemas import FaceRegisterRequest, FaceCheckRequest
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/faces", tags=["人脸识别"])


# ==========================================
# 静默活体检测（图像纹理 + 频域分析）
# ==========================================
def _liveness_check(rgb_img: np.ndarray, face_location: tuple) -> tuple:
    """
    基于图像纹理与频域特征的静默活体检测。
    检测翻拍屏幕照片的摩尔纹、纹理模糊、色彩饱和度异常等特征。
    返回 (is_alive: bool, reason: str)
    """
    top, right, bottom, left = face_location
    face_roi = rgb_img[top:bottom, left:right]
    if face_roi.size == 0:
        return False, "人脸区域无效"

    gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_RGB2GRAY)

    # ---- 检测1：拉普拉斯方差（屏幕翻拍图像清晰度异常偏低） ----
    laplacian_var = cv2.Laplacian(gray_roi, cv2.CV_64F).var()
    if laplacian_var < 30:
        return False, "图像纹理模糊，疑似非活体"

    # ---- 检测2：频域摩尔纹检测（屏幕翻拍特有的高频周期性条纹） ----
    resized = cv2.resize(gray_roi, (128, 128))
    f_transform = np.fft.fft2(resized)
    f_shift = np.fft.fftshift(f_transform)
    magnitude = np.log(np.abs(f_shift) + 1)
    h, w = magnitude.shape
    center_h, center_w = h // 2, w // 2
    low_freq = magnitude[center_h - 16:center_h + 16, center_w - 16:center_w + 16].mean()
    high_freq = magnitude.mean()
    freq_ratio = high_freq / (low_freq + 1e-6)
    if freq_ratio > 0.85:
        return False, "检测到屏幕摩尔纹特征，疑似照片翻拍"

    # ---- 检测3：色彩饱和度分析（屏幕显示的人脸色彩分布异于真人） ----
    hsv_roi = cv2.cvtColor(face_roi, cv2.COLOR_RGB2HSV)
    saturation = hsv_roi[:, :, 1]
    sat_mean = float(saturation.mean())
    sat_std = float(saturation.std())
    if sat_mean < 25 or sat_std < 10:
        return False, "面部色彩特征异常，疑似非活体"

    return True, "通过"


# ==========================================
# 查询当前学生人脸注册状态
# ==========================================
@router.get("/my_status")
async def my_face_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sf = db.query(StudentFeature).filter(StudentFeature.user_id == current_user.id).first()
    return {"registered": sf is not None, "student_id": sf.student_id if sf else None}


# ==========================================
# 人脸录入（视觉大脑）
# ==========================================
@router.post("/register")
async def register_face(
    data: FaceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # 权限校验：学生只能录入自己的人脸
        if current_user.role == "student":
            if data.student_id != current_user.username:
                raise HTTPException(status_code=403, detail="学生只能录入自己的人脸！")
            if data.name != current_user.real_name:
                data.name = current_user.real_name  # 强制使用真实姓名

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
        feature_blob = feature_vector.tobytes()

        # 步骤 C：数据持久化（支持重新录入覆盖）
        existing_student = db.query(StudentFeature).filter(StudentFeature.student_id == data.student_id).first()
        if existing_student:
            # 学生自己重新录入 或 教师/管理员覆盖 → 更新特征
            if current_user.role == "student" and existing_student.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="该学号已被其他账号录入！")
            existing_student.face_encoding = feature_blob
            existing_student.name = data.name
            existing_student.user_id = current_user.id
            db.commit()
            return {"status": "success", "message": f"已更新 {data.name} 的面部特征！"}

        new_student = StudentFeature(
            student_id=data.student_id,
            name=data.name,
            face_encoding=feature_blob,
            user_id=current_user.id,
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
async def check_in_face(
    data: FaceCheckRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
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

        # 步骤 A-2：活体检测（拦截照片/屏幕翻拍代打卡）
        is_alive, liveness_reason = _liveness_check(rgb_img, face_locations[0])
        if not is_alive:
            print(f"🚫 活体检测未通过：{liveness_reason}")
            return {
                "status": "fail",
                "message": f"活体检测未通过：{liveness_reason}，请确保本人真实面对摄像头！",
            }

        unknown_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]

        # 步骤 B：只拉取该排课对应班级的学生特征（班级范围过滤）
        class_ids = schedule.resolved_class_ids or ([schedule.class_id] if schedule.class_id else [])
        class_student_ids = (
            db.query(class_students.c.student_feature_id)
            .filter(class_students.c.class_id.in_(class_ids))
            .distinct()
            .subquery()
        )
        scoped_students = (
            db.query(StudentFeature)
            .filter(StudentFeature.id.in_(db.query(class_student_ids)))
            .all()
        )
        if not scoped_students:
            raise HTTPException(status_code=400, detail="该班级未录入任何学生档案！")

        known_encodings = [np.frombuffer(s.face_encoding, dtype=np.float64) for s in scoped_students]

        # 步骤 C：计算欧氏距离
        distances = face_recognition.face_distance(known_encodings, unknown_encoding)
        best_match_index = np.argmin(distances)
        min_distance = distances[best_match_index]

        # 步骤 D：阈值判定
        THRESHOLD = 0.45
        if min_distance <= THRESHOLD:
            matched_student = scoped_students[best_match_index]

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

            # 步骤 F：判定迟到（超过上课时间15分钟算迟到，使用 timedelta 避免溢出）
            now = datetime.now()
            scheduled_start = datetime.combine(now.date(), schedule.start_time)
            late_threshold = scheduled_start + timedelta(minutes=15)
            if now > late_threshold:
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
