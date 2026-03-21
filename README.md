# SnapSign

这个仓库分成前后端两部分：

- backend：FastAPI + SQLAlchemy + MySQL
- frontend：Vue 3 + TypeScript + Vite

为了方便在另一台电脑恢复环境，依赖文件已经拆分为：

- backend/environment.yml：Conda 环境文件，适合直接创建后端运行环境
- backend/requirements.txt：后端 pip 依赖文件
- backend/requirements-vision.txt：摄像头与人脸识别脚本的额外依赖
- frontend/package.json 和 frontend/package-lock.json：前端依赖与锁定版本

## 1. 后端环境

二选一即可。

### 方案 A：使用 Conda

在仓库根目录执行：

```powershell
conda env create -f backend/environment.yml
conda activate snapsign
```

### 方案 B：使用 venv + pip

在仓库根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend/requirements.txt
```

如果你还需要运行摄像头测试脚本，再额外安装：

```powershell
pip install -r backend/requirements-vision.txt
```

## 2. 前端环境

前端建议使用 Node.js 20.19+ 或 22.12+。

在仓库根目录执行：

```powershell
cd frontend
npm ci
```

## 3. 启动项目

### 启动后端

```powershell
cd backend
python -m app.main
```

### 启动前端

```powershell
cd frontend
npm run dev
```

## 4. 额外说明

- 数据库连接目前写死在 backend/app/db/session.py，需要在另一台电脑按实际 MySQL 用户名、密码、端口修改。
- backend/scripts/test_camera_face.py 依赖摄像头权限，并且 face-recognition 在部分 Windows 环境下可能需要更长安装时间。