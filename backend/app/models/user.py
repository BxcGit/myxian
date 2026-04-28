from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("用户名至少3位")
        if len(v) > 50:
            raise ValueError("用户名最多50位")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 4:
            raise ValueError("密码长度至少8位")
        if len(v) > 128:
            raise ValueError("密码长度最多128位")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserSettings(BaseModel):
    id: int
    username: str
    manual_timeout: int = 3600
    manual_keywords: str = "。"
    manual_exit_keywords: str = "退出"


class UserSettingsUpdate(BaseModel):
    manual_timeout: int | None = None
    manual_keywords: str | None = None
    manual_exit_keywords: str | None = None
