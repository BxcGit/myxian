## 架构优化点

### 1. 项目架构

```
myxianyu/
├── frontend/                    # Vue 3 SPA
│   ├── src/
│   │   ├── api.js              # Axios API 调用
│   │   ├── views/              # 页面组件
│   │   │   ├── Home.vue        # 主布局
│   │   │   ├── Dashboard.vue   # 首页
│   │   │   ├── Account.vue     # 账号管理
│   │   │   ├── Product.vue     # 商品管理
│   │   │   ├── Session.vue     # 会话管理
│   │   │   └── UserSettings.vue # 用户设置
│   │   ├── components/         # 组件
│   │   │   ├── ChatPanel.vue   # 聊天面板
│   │   │   ├── ChatMessage.vue # 消息
│   │   │   └── SessionList.vue # 会话列表
│   │   └── router/             # 路由配置
│   └── vite.config.js
└── backend/
    └── app/
        ├── main.py              # FastAPI 入口
        ├── config.py            # 配置 (XianyuConfig)
        ├── database.py          # SQLite 初始化
        ├── routers/             # API 路由
        │   ├── auth.py          # /auth/*
        │   ├── xianyu_account.py # /xianyu-accounts/*
        │   ├── product.py       # /products/*
        │   └── session.py       # /sessions/*
        ├── models/              # Pydantic 模型
        │   ├── user.py
        │   ├── xianyu_account.py
        │   ├── product.py
        │   ├── session.py
        │   └── message.py
        └── xianyu/              # 闲鱼核心模块
            ├── ws_client.py     # WebSocket 客户端
            ├── xianyu_api.py    # 闲鱼 API
            ├── handler_message.py # 消息处理
            ├── account_context.py # 全局账号上下文
            ├── manual_manager.py # 人工接管模式
            ├── token_manager.py  # Token 管理
            ├── heart_beat.py    # 心跳
            └── parser.py        # 消息解析
```

### 2. 核心业务流程

```
用户添加闲鱼账号(Cookie)
        ↓
WebSocket 客户端连接闲鱼服务器 (wss://wss-goofish.dingtalk.com/)
        ↓
接收消息 → 消息解析 → 保存到数据库
        ↓
网页端管理会话、查看消息
```

### 3. 数据库表结构

| 表名 | 说明 |
|------|------|
| users | 用户表（含人工接管配置字段） |
| xianyu_accounts | 闲鱼账号表 |
| products | 商品表 |
| sessions | 会话表 |
| messages | 消息表 |

### 4. API 路由

| 路由 | 说明 |
|------|------|
| POST /auth/register | 用户注册 |
| POST /auth/login | 用户登录 |
| GET/POST/PUT/DELETE /xianyu-accounts/* | 账号 CRUD + 启动/停止 |
| GET/POST/PUT/DELETE /products/* | 商品 CRUD + 同步 |
| GET/POST/DELETE /sessions/* | 会话 CRUD |
| GET /sessions/{id}/messages | 获取会话消息 |
| GET /sessions/messages/recent | 最近消息 |

### 5. 闲鱼 WebSocket 模块

| 模块 | 职责 |
|------|------|
| WSClient | WebSocket 连接管理、消息收发 |
| XianyuApis | 闲鱼 API 调用（Token 获取、商品信息） |
| XianyuMessageHandler | 消息解析、订单处理、聊天消息处理 |
| AccountContext | 全局账号上下文，管理所有 WSClient |
| ManualModeManager | 人工接管模式（单例） |
| TokenManager | Token 刷新管理 |
| XianyuHeartbeat | 心跳维护 |
| XianyuMessageParser | 消息解密、解析 |

### 6. 待开发/优化点

- [ ] AI 自动回复功能集成
- [ ] 订单自动处理
- [ ] 消息推送通知
- [ ] WebSocket 实时通信优化
### 7. 架构与代码优化点

#### 7.1 架构优化

| 问题 | 描述 | 状态 | 建议 |
|------|------|------|------|
| **缺乏认证机制** | 登录只返回 user_id，无 JWT/Token；所有 API 无权限校验 | ✅ 已实现 JWT 认证 | 引入 JWT 或 Session 认证 |
| **用户数据隔离缺失** | `xianyu_accounts` 表的 user_id 在 create_account 时写死为 1 | ✅ 已实现用户隔离 | 实现用户关联和权限隔离 |
| **WebSocket 无前端推送** | 前端靠轮询（10秒间隔）获取消息，延迟高 | TODO | 后端 WebSocket 推送新消息到前端 |
| **缺乏异步任务队列** | Token 刷新、消息处理等都是直接调用，缺乏统一管理 | TODO | 引入 TaskQueue 或 BackgroundTasks |
| **数据库连接无池化** | 每个请求打开/关闭连接，高并发时性能差 | TODO | 使用 aiosqlite + 连接池 |
| **配置无法运行时更新** | XianyuConfig 只从环境变量加载 | TODO | 支持运行时配置更新 API |
| **sys.exit() 硬退出** | xianyu_api.py:152 调用 sys.exit(1)，无法恢复 | TODO | 改为抛异常让调用方处理 |
| **日志体系不完善** | 日志分散，无请求追踪，无结构化日志 | ✅ 已实现统一日志 | 引入 structlog 或统一日志格式 |

#### 7.2 代码 Bug

| 文件 | 行号 | 问题 | 状态 |
|------|------|------|------|
| token_manager.py | 66 | `on_refreshed` 变量未定义就使用，代码逻辑错误 | ✅ 已修复 |
| session.py | 82 | `conn.close()` 后又使用 `cursor`，cursor 已无效 | ✅ 已修复 |
| ws_client.py | 227 | `self._tasks.append(self._token_manager.run_loop())` run_loop() 返回协程而非 Task | ✅ 已修复 |

#### 7.3 代码规范与可维护性

| 问题 | 描述 |
|------|------|
| **重复数据库操作** | routers 中大量重复的 try/finally、conn.open/close 模式 |
| **魔法数字/字符串** | 多处硬编码的时间间隔、阈值、状态值 |
| **异常过于宽泛** | `except Exception` 捕获所有异常，掩盖真实错误 |
| **缺乏类型注解** | handler_message.py、ws_client.py 等核心文件缺少类型提示 |
| **注释掉的调试代码** | ws_client.py:248 注释的调试打印未清理 |
| **单例模式混用** | ManualModeManager 用单例，AccountContext 用类方法（类似单例但不一致） | ✅ 已统一为经典单例模式 |

#### 7.4 安全问题

| 问题 | 描述 | 状态 |
|------|------|------|
| **CORS 全开** | `allow_origins=["*"]` 生产环境应限制 | TODO |
| **Cookie 明文传输** | xianyu_accounts 表的 cookie 字段无加密存储 | TODO |
| **密码强度** | RegisterRequest 无密码复杂度校验 | ✅ 已实现 |
| **SQL 拼接** | 部分路由用 f-string 拼接 SQL（如 auth.py:109），存在注入风险 | ⚠️ 部分修复（参数化查询） |

#### 7.5 前端优化

| 问题 | 描述 |
|------|------|
| **轮询机制** | Dashboard 用 setInterval 轮询，应改为 WebSocket |
| **无错误边界** | Vue 组件无统一的错误处理 |
| **API 封装简单** | api.js 无请求/响应拦截器，无统一错误处理 |
| **未分类的环境变量** | Vite 配置直接暴露 API 地址 |
