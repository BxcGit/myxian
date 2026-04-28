from pydantic import BaseModel


class XianyuAccountCreate(BaseModel):
    xianyu_name: str
    cookie: str = ""
    user_agent: str | None = ""


class XianyuAccountUpdate(BaseModel):
    xianyu_name: str | None = None
    cookie: str | None = None
    user_agent: str | None = None


class XianyuAccount(BaseModel):
    id: int
    user_id: int
    xianyu_name: str
    cookie: str
    user_agent: str | None = ""
    is_active: bool = False  # 仅用于响应，不存储到数据库
