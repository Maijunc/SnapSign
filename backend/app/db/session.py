# backend/app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 替换为你自己的 MySQL 用户名和密码
# 格式: mysql+pymysql://用户名:密码@主机地址:端口/数据库名
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/snapsign"

# 创建数据库引擎
# echo=True 会在控制台打印生成的 SQL 语句，方便调试
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

# 创建数据库会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有模型的基类
Base = declarative_base()

# 定义一个获取数据库会话的依赖函数，供后续 API 接口使用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()