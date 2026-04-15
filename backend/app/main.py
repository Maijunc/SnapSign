# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel # 👉 导入 BaseModel 用于接收 JSON
import uvicorn

# 引入数据库引擎和基类
from app.db.session import engine, Base
# 务必在这里导入你的模型文件，否则 SQLAlchemy 不知道有哪些表需要创建
from app.models import domain 

# 核心：利用 SQLAlchemy 自动在 MySQL 中创建表结构 (如果表已存在则忽略)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SnapSign API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👇 1. 定义前端传过来的数据格式
class FaceRegisterRequest(BaseModel):
    student_id: str
    name: str
    image_base64: str

# 👇 2. 接收前端请求的 API
@app.post("/api/v1/faces/register")
async def register_face(data: FaceRegisterRequest):
    # 这里我们先不连数据库，只打印出来证明我们收到了！
    print(f"\n🎉 收到前端发来的数据了！")
    print(f"学号: {data.student_id}")
    print(f"姓名: {data.name}")
    print(f"图片 Base64 长度: {len(data.image_base64)} 字符\n")
    
    # 返回成功信息给前端
    return {
        "status": "success", 
        "message": f"已成功接收 {data.name} 的人脸数据！"
    }

# ... (这里保留你之前写的 CORS 配置和 ping 接口) ...

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)