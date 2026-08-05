# ERP 系统 — 登录模块

基于 FastAPI + Vue 3 的 ERP 登录全栈实现，使用 JWT 认证。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python FastAPI + SQLAlchemy + SQLite |
| 前端 | Vue 3 + Vite + Vue Router |
| 认证 | JWT Access Token |

## 快速启动

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API 文档：http://127.0.0.1:8000/docs

默认账户：`admin` / `admin123`（首次启动自动创建）

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://127.0.0.1:5173

前端通过 Vite 代理将 `/api` 请求转发至后端 `8000` 端口。

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT |
| GET | `/api/auth/me` | 获取当前用户信息（需 Bearer Token） |
| GET | `/api/health` | 健康检查 |

## 用户表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| username | String(50) | 用户名，唯一 |
| hashed_password | String(255) | bcrypt 哈希密码 |
| role | String(50) | 角色（如 admin / user） |

## 运行测试

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```
