# myxianyu

闲鱼账号管理后端服务，基于 FastAPI + Vue 3。

## 技术栈

- **后端**: FastAPI + Python + SQLite
- **前端**: Vue 3 + Vite + Element Plus
- **WebSocket**: 闲鱼 WebSocket 实时消息推送

## 项目结构

```
myxianyu/
├── frontend/           # Vue 3 前端
│   ├── src/
│   │   ├── api.js      # API 调用
│   │   ├── views/      # 页面组件
│   │   ├── components/ # 公共组件
│   │   └── router/     # 路由配置
│   └── vite.config.js
└── backend/
    └── app/
        ├── main.py         # FastAPI 入口
        ├── config.py       # 配置文件
        ├── database.py     # 数据库
        ├── models/         # 数据模型
        ├── routers/        # API 路由
        └── xianyu/         # 闲鱼模块
            ├── ws_client.py        # WebSocket 客户端
            ├── account_context.py  # 全局账号管理
            ├── heart_beat.py       # 心跳管理
            ├── token_manager.py    # Token 管理
            ├── handler_message.py  # 消息处理
            ├── parser.py           # 消息解析
            └── xianyu_api.py       # 闲鱼 API
```

## 环境安装

### 后端

```bash
conda create -n my_xianyu python=3.12
conda activate my_xianyu
cd backend
pip install -r requirements.txt
```

### 前端

```bash
cd frontend
pnpm install
```

## 启动项目

### 后端

```bash
conda activate my_xianyu
cd backend
python run.py
```

后端服务启动在 http://localhost:8000

### 前端

```bash
cd frontend
pnpm dev
```

前端服务启动在 http://localhost:5173

## API 接口

### 认证

- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录

### 闲鱼账号

- `GET /xianyu-accounts/` - 获取所有账号
- `GET /xianyu-accounts/{id}` - 获取单个账号
- `POST /xianyu-accounts/` - 创建账号
- `PUT /xianyu-accounts/{id}` - 更新账号
- `DELETE /xianyu-accounts/{id}` - 删除账号

### 商品

- `GET /products/` - 获取所有商品
- `GET /products/{id}` - 获取单个商品
- `POST /products/` - 创建商品
- `PUT /products/{id}` - 更新商品
- `DELETE /products/{id}` - 删除商品

## 打包发布

本项目支持将前端和后端打包为独立的 Windows 可执行文件（exe）。

### 前置要求

- Python 3.12+
- Node.js 18+ (前端构建)
- pnpm (或 npm)
- PyInstaller

```bash
# 安装 PyInstaller
pip install pyinstaller
```

### 打包步骤

打包脚本位于 `backend/build.py`，支持三种模式：

#### 方式一：一键打包（推荐）

```bash
cd backend
python build.py
```

**执行流程：**
1. 检查前端是否已构建（`frontend/dist/`）
2. 如未构建，自动执行 `pnpm install` 安装前端依赖
3. 自动执行 `pnpm build` 构建前端
4. 清理旧的构建文件
5. 执行 PyInstaller 打包后端为 exe
6. 将前端静态文件复制到 exe 同目录

#### 方式二：分步打包

```bash
# 1. 先构建前端
cd frontend
pnpm install
pnpm build

# 2. 再打包后端
cd backend
python build.py
```

#### 方式三：清理后重新打包

```bash
cd backend
python build.py clean   # 清理构建文件
python build.py         # 重新打包
```

### 打包输出

打包完成后，产物位于 `dist/myxianyu/` 目录：

```
dist/myxianyu/
├── myxianyu.exe           # 主程序
├── myxianyu/              # 依赖目录
│   └── ...
└── static/                # 前端静态文件
    ├── index.html
    ├── assets/
    └── ...
```

### 运行打包后的程序

```bash
cd dist/myxianyu
myxianyu.exe
```

访问 http://localhost:8000 即可使用。

### 常见问题

**Q: 打包失败，提示找不到模块**
- 确保 `backend/.env` 文件存在
- 确保 `prompts/` 目录存在

**Q: 前端构建失败**
- 确保 Node.js 版本 >= 18
- 确保 pnpm 已安装：`npm install -g pnpm`

**Q: PyInstaller 打包后运行报错**
- 检查是否所有 hiddenimports 都已包含在 `app.spec` 中

## 配置说明

可通过环境变量配置闲鱼 WebSocket 相关参数：

| 环境变量                      | 默认值 | 说明                         |
| ----------------------------- | ------ | ---------------------------- |
| XIANYU_HEARTBEAT_INTERVAL     | 15     | 心跳间隔（秒）               |
| XIANYU_HEARTBEAT_TIMEOUT      | 5      | 心跳超时（秒）               |
| XIANYU_TOKEN_REFRESH_INTERVAL | 3600   | Token 刷新间隔（秒）         |
| XIANYU_TOKEN_RETRY_INTERVAL   | 300    | Token 刷新失败重试间隔（秒） |
| XIANYU_MESSAGE_EXPIRE_TIME    | 3600   | 消息过期时间（秒）           |
