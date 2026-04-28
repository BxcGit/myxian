import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import auth, xianyu_account, product, session
from .xianyu.account_context import AccountContext
from .ai_agent import AIAgent, set_agent
from .config import AIConfig
from .utils.logger import get_logger
from .utils.middleware import RequestLogMiddleware
from .core.path_utils import is_frozen, STATIC_DIR, ensure_dirs

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 获取应用日志器
app_logger = get_logger("app", logging.INFO, "app.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("应用启动中...")
    # 确保必要的目录存在
    ensure_dirs()
    init_db()
    # 初始化账号上下文，加载数据库中的账号信息（不自动启动客户端）
    AccountContext.initialize()
    # 初始化AI Agent
    ai_config = AIConfig.from_env()
    agent = AIAgent(ai_config)
    task = await agent.start()
    if task:
        app_logger.info("AI Agent 启动完成")
    else:
        app_logger.warning("AI Agent 启动失败")
    await set_agent(agent)
    app_logger.info("应用启动完成")
    yield
    # 关闭所有WebSocket客户端并清理资源
    app_logger.info("应用关闭中...")
    if task:
        task.cancel()
        app_logger.info("AI Agent 已取消")
    from .ai_agent.ai_agent import _agent_instance as _ai_module_agent
    if _ai_module_agent and _ai_module_agent._started:
        await _ai_module_agent.shutdown()
        _ai_module_agent = None
    await AccountContext.shutdown()
    app_logger.info("应用已关闭")


app = FastAPI(
    lifespan=lifespan,
    title="闲鱼自动回复系统",
    version="1.0.0",
)

# 添加请求日志中间件
app.add_middleware(RequestLogMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(xianyu_account.router)
app.include_router(product.router)
app.include_router(session.router)

# 打包模式下挂载静态文件
if is_frozen() and STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
