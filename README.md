# Lounger Test Platform

一个轻量级的 Web 测试管理平台，基于 Git 仓库管理测试用例，支持可视化的用例浏览、任务编排、自动化执行与报告查看。

## 架构

```
platform/
├── frontend/          # Vue 3 前端应用
│   └── src/
│       ├── views/         # 页面组件
│       ├── components/    # 通用组件
│       ├── router/        # 路由配置
│       ├── api/           # API 客户端
│       └── main.js
├── backend/           # FastAPI 后端服务
│   └── app/
│       ├── routers/       # API 路由
│       ├── models/        # 数据模型 (SQLAlchemy)
│       ├── schemas/       # Pydantic 数据校验
│       ├── services/      # 业务逻辑层
│       ├── config.py      # 配置
│       └── database.py    # 数据库初始化
├── e2e/               # Playwright 端到端测试
└── README.md
```

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | Vue 3 + Composition API | 响应式 UI |
| 前端 | Element Plus | 组件库（表格、对话框、表单等） |
| 前端 | Vue Router | 路由管理（Hash 模式） |
| 前端 | Axios | HTTP 客户端 |
| 前端 | Vite | 构建与开发服务器 |
| 后端 | FastAPI | Web 框架 |
| 后端 | SQLAlchemy (Async) | ORM + 数据库操作 |
| 后端 | aiosqlite | SQLite 异步驱动 |
| 后端 | pytest | 测试执行引擎 |
| 测试 | Playwright | E2E 自动化测试 |

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- npm >= 9

### 后端启动

```bash
cd backend

# 安装依赖
pip install -e ".[dev]"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

服务默认监听 `http://localhost:8000`，API 文档访问 `http://localhost:8000/docs`。

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器默认监听 `http://localhost:5173`，通过 Vite Proxy 将 `/api` 请求转发到后端 `8000` 端口。

### 端到端测试

```bash
cd frontend

# 运行全部 Playwright 测试
npx playwright test

# 运行指定测试文件
npx playwright test e2e/project-detail.spec.js

# 查看 HTML 报告
npx playwright show-report
```

Playwright 会自动启动前端开发服务器（端口 5176），测试用例覆盖了用例管理、任务管理、任务报告等核心功能。

## 功能模块

### 项目管理

- **项目列表**：卡片式布局展示所有项目，支持添加、删除项目
- **项目切换**：顶部下拉框快速切换当前项目
- **Git 集成**：输入仓库地址自动克隆，管理测试源码

### 用例管理

- **目录树浏览**：左侧树形结构展示项目文件结构和测试用例
- **用例选中**：勾选用例，实时统计选中数量，支持全选/取消全选
- **用例执行**：选中用例后一键运行，右侧实时输出日志（SSE 流式推送）
- **测试收集**：自动从测试文件中解析 pytest 用例并入库

### 任务管理

- **任务 CRUD**：创建、编辑、删除测试任务
- **用例选择器**：树形勾选任务关联的用例，支持搜索
- **任务状态**：未运行 / 运行中 / 已完成
- **任务执行**：一键执行任务，自动生成测试报告
- **分页查询**：支持分页浏览任务列表

### 任务报告

- **运行记录**：查看每个任务的历史运行记录
- **筛选查询**：按任务名称（可搜索下拉）、日期范围筛选
- **分页浏览**：支持分页查看报告
- **详情查看**：查看单次运行的详细用例执行结果

### 数据模型

| 表 | 说明 |
|---|---|
| `projects` | 项目（Git 仓库、用例目录） |
| `test_cases` | 测试用例（nodeid、文件路径、描述） |
| `test_reports` | 测试报告（通过/失败/跳过统计） |
| `report_details` | 报告详情（每条用例的执行结果） |
| `tasks` | 测试任务（关联的用例列表） |
| `task_runs` | 任务运行记录（状态、统计、关联报告） |

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/projects` | 项目列表/创建 |
| GET/PUT/DELETE | `/api/projects/{id}` | 项目详情/更新/删除 |
| GET | `/api/projects/{id}/cases/tree` | 用例树 |
| POST | `/api/projects/{id}/cases/run` | 运行用例 |
| GET | `/api/projects/{id}/reports` | 报告列表 |
| GET | `/api/projects/{id}/reports/{rid}` | 报告详情 |
| GET/POST | `/api/projects/{id}/tasks` | 任务列表/创建（分页） |
| PUT | `/api/projects/{id}/tasks/{tid}` | 编辑任务 |
| DELETE | `/api/projects/{id}/tasks/{tid}` | 删除任务 |
| POST | `/api/projects/{id}/tasks/{tid}/run` | 执行任务 |
| GET | `/api/projects/{id}/tasks/runs/all` | 运行记录（分页+筛选） |
| GET | `/api/stream/{run_id}` | SSE 日志流 |

## 开发指南

### 数据库

后端使用 SQLite（文件存储 `backend/lounger_platform.db`），首次启动自动建表。可通过环境变量 `DATABASE_URL` 切换其他数据库。

### 配置

主要配置项在 `backend/app/config.py`：

```python
DATABASE_URL     # 数据库连接串，默认 SQLite
PROJECTS_DIR     # 项目克隆目录
REPORTS_DIR      # 报告存储目录
```

### 前端代理

Vite 开发服务器自动将 `/api` 请求代理到后端，配置在 `vite.config.js`：

```js
proxy: {
  '/api': { target: 'http://localhost:8000', changeOrigin: true }
}
```

## License

MIT
