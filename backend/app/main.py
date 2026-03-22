# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 引入数据库引擎和基类
from app.db.session import engine, Base
# 务必在这里导入你的模型文件，否则 SQLAlchemy 不知道有哪些表需要创建
from app.models import domain 

# 核心：利用 SQLAlchemy 自动在 MySQL 中创建表结构 (如果表已存在则忽略)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SnapSign API")

# ... (这里保留你之前写的 CORS 配置和 ping 接口) ...

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)