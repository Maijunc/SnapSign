# backend/app/main.py
import base64
import numpy as np
import cv2
import face_recognition

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # 👉 导入 BaseModel 用于接收 JSON
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uvicorn


# 引入数据库引擎和基类
from app.db.session import engine, Base
# 务必在这里导入你的模型文件，否则 SQLAlchemy 不知道有哪些表需要创建
from app.models import domain 

# ==========================================
# 1. 数据库配置 (记忆中枢)
# ==========================================
# 为了快速跑通，这里先用本地的 snapsign.db 数据库文件
SQLALCHEMY_DATABASE_URL = "sqlite:///./snapsign.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 定义学生特征表
class StudentFeature(Base):
    __tablename__ = "student_features"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, unique=True, index=True)
    name = Column(String)
    face_encoding = Column(LargeBinary) # 重点：将 128 维向量存为 BLOB 二进制格式

# 启动时自动在本地创建这个数据库表
Base.metadata.create_all(bind=engine)

# 获取数据库会话的依赖函数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. FastAPI 应用初始化
# ==========================================

app = FastAPI(title="SnapSign API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class FaceRegisterRequest(BaseModel):
    student_id: str
    name: str
    image_base64: str


# ==========================================
# 3. 核心 API：人脸录入与特征提取 (视觉大脑)
# ==========================================
@app.post("/api/v1/faces/register")
async def register_face(data: FaceRegisterRequest, db: Session = Depends(get_db)):
    try:
        # --- 步骤 A：图片解码 ---
        # 剥离前端传过来的 "data:image/jpeg;base64," 前缀
        encoded_data = data.image_base64.split(",")[1] if "," in data.image_base64 else data.image_base64
        img_data = base64.b64decode(encoded_data)
        
        # 将二进制转化为 OpenCV 能看懂的 numpy 数组 (BGR格式)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # --- 步骤 B：特征提取 ---
        # face_recognition 需要 RGB 格式，先做转换
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 寻找画面中的人脸位置
        face_locations = face_recognition.face_locations(rgb_img)
        if not face_locations:
            raise HTTPException(status_code=400, detail="照片中未检测到人脸，请正对摄像头！")
        if len(face_locations) > 1:
            raise HTTPException(status_code=400, detail="检测到多张人脸，请确保画面中只有你一个人！")

        # 提取 128 维人脸特征向量
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        feature_vector = face_encodings[0] # 获取第一个人脸的向量

        # --- 步骤 C：数据持久化落地 ---
        # 检查该学号是否已经录入过
        existing_student = db.query(StudentFeature).filter(StudentFeature.student_id == data.student_id).first()
        if existing_student:
            raise HTTPException(status_code=400, detail="该学号已存在，请勿重复录入！")

        # 将 numpy 数组序列化为字节流（二进制），存入数据库
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

    except HTTPException as he:
        raise he
    except Exception as e:
        print("❌ 后端发生错误:", str(e))
        raise HTTPException(status_code=500, detail="服务器特征提取失败，请检查控制台日志。")

# 考勤打卡的数据模型
class FaceCheckRequest(BaseModel):
    image_base64: str

# ==========================================
# 4. 核心 API：考勤打卡与人脸比对 (记忆检索)
# ==========================================
@app.post("/api/v1/faces/check_in")
async def check_in_face(data: FaceCheckRequest, db: Session = Depends(get_db)):
    try:
        # 步骤 A：图片解码与当前人脸特征提取
        encoded_data = data.image_base64.split(",")[1] if "," in data.image_base64 else data.image_base64
        img_data = base64.b64decode(encoded_data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_img)
        if not face_locations:
            raise HTTPException(status_code=400, detail="未检测到人脸，请正对摄像头！")
        
        # 提取当前站在屏幕前的人的 128维特征
        unknown_encoding = face_recognition.face_encodings(rgb_img, face_locations)[0]

        # 步骤 B：从数据库拉取所有已注册的【记忆】
        all_students = db.query(StudentFeature).all()
        if not all_students:
            raise HTTPException(status_code=400, detail="系统未录入任何学生档案！")

        # 将数据库里的 BLOB 还原成 numpy 数组 (注意：恢复为 float64 类型)
        known_encodings = [np.frombuffer(student.face_encoding, dtype=np.float64) for student in all_students]

        # 步骤 C：核心算法 - 计算欧氏距离 (距离越小越像)
        distances = face_recognition.face_distance(known_encodings, unknown_encoding)
        
        # 找到距离最小的那个人的索引
        best_match_index = np.argmin(distances)
        min_distance = distances[best_match_index]

        # 步骤 D：判定阈值 (通常 0.4~0.45 为严格匹配)
        THRESHOLD = 0.45
        if min_distance <= THRESHOLD:
            matched_student = all_students[best_match_index]
            print(f"✅ 考勤成功！识别为: {matched_student.name} (差异度: {min_distance:.3f})")
            return {
                "status": "success",
                "message": f"签到成功！欢迎你，{matched_student.name}",
                "student_name": matched_student.name,
                "distance": float(min_distance)
            }
        else:
            print(f"❌ 考勤失败！最小差异度: {min_distance:.3f}。陌生人拦截机制已触发。")
            return {
                "status": "fail",
                "message": "未匹配到档案，请确认是否已录入人脸！"
            }

    except HTTPException as he:
        raise he
    except Exception as e:
        print("❌ 考勤接口报错:", str(e))
        raise HTTPException(status_code=500, detail="服务器比对失败。")
    
# ==========================================
# 5. 查询所有已录入的学生档案 (不返回庞大的特征向量)
# ==========================================
@app.get("/api/v1/students")
async def get_all_students(db: Session = Depends(get_db)):
    try:
        # 查询数据库中所有的学生，但排除了 face_encoding 这个二进制大文件
        students = db.query(StudentFeature.id, StudentFeature.student_id, StudentFeature.name).all()
        # 组装成 JSON 列表返回给前端
        result = [{"id": s.id, "student_id": s.student_id, "name": s.name} for s in students]
        return {"status": "success", "data": result}
    except Exception as e:
        print("❌ 查询学生列表失败:", str(e))
        raise HTTPException(status_code=500, detail="查询数据库失败")

# ==========================================、
# 6. 删除指定学生的档案
# ==========================================
@app.delete("/api/v1/students/{student_id}")
async def delete_student(student_id: str, db: Session = Depends(get_db)):
    try:
        student = db.query(StudentFeature).filter(StudentFeature.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="未找到该学生档案")
        
        # 从数据库中硬删除
        db.delete(student)
        db.commit()
        print(f"🗑️ 成功删除学生档案: {student.name} ({student_id})")
        return {"status": "success", "message": f"成功删除 {student.name} 的档案"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print("❌ 删除学生失败:", str(e))
        raise HTTPException(status_code=500, detail="删除数据库记录失败")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)