import asyncio
from fastapi import APIRouter, HTTPException, Depends

from ..database import get_db_connection
from ..models.xianyu_account import (
    XianyuAccountCreate,
    XianyuAccountUpdate,
    XianyuAccount,
)
from ..xianyu.account_context import AccountContext
from ..utils.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/xianyu-accounts", tags=["xianyu-accounts"])


@router.get("/", response_model=list[XianyuAccount])
async def list_accounts(current_user: CurrentUser = Depends(get_current_user)):
    """获取当前用户的所有账号"""
    if AccountContext.is_initialized():
        accounts = AccountContext.get_all_accounts()
        # 只返回属于当前用户的账号
        result = []
        for acc in accounts:
            if acc.user_id != current_user.user_id:
                continue
            acc_dict = acc.model_dump()
            acc_dict["is_active"] = AccountContext.is_account_active(acc.id)
            result.append(acc_dict)
        return result

    # 降级到数据库查询
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, xianyu_name, cookie, user_agent FROM xianyu_accounts WHERE user_id = ?",
        (current_user.user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        acc_dict = dict(row)
        acc_dict["is_active"] = False
        result.append(acc_dict)
    return result


@router.get("/{account_id}", response_model=XianyuAccount)
async def get_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取指定账号"""
    # 优先从缓存获取
    if AccountContext.is_initialized():
        account = AccountContext.get_account(account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="账号不存在")
        # 权限校验
        if account.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="无权限访问此账号")
        acc_dict = account.model_dump()
        acc_dict["is_active"] = AccountContext.is_account_active(account_id)
        return acc_dict

    # 降级到数据库查询
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, xianyu_name, cookie, user_agent FROM xianyu_accounts WHERE id = ?",
        (account_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    # 权限校验
    if row["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权限访问此账号")
    acc_dict = dict(row)
    acc_dict["is_active"] = AccountContext.is_account_active(account_id) if AccountContext.is_initialized() else False
    return acc_dict


@router.post("/", response_model=XianyuAccount)
async def create_account(
    account: XianyuAccountCreate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """创建账号（自动关联到当前用户）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO xianyu_accounts (user_id, xianyu_name, cookie, user_agent) VALUES (?, ?, ?, ?)",
        (current_user.user_id, account.xianyu_name, account.cookie, account.user_agent),
    )
    conn.commit()
    account_id = cursor.lastrowid
    conn.close()

    new_account = XianyuAccount(
        id=account_id,
        user_id=current_user.user_id,
        xianyu_name=account.xianyu_name,
        cookie=account.cookie,
        user_agent=account.user_agent
    )

    # 更新缓存（不自动启动客户端）
    if AccountContext.is_initialized():
        AccountContext.add_account(new_account)

    acc_dict = new_account.model_dump()
    acc_dict["is_active"] = False
    return acc_dict


@router.put("/{account_id}", response_model=XianyuAccount)
async def update_account(
    account_id: int,
    account: XianyuAccountUpdate,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新账号"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, xianyu_name, cookie, user_agent FROM xianyu_accounts WHERE id = ?",
        (account_id,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="账号不存在")

    # 权限校验
    if row["user_id"] != current_user.user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="无权限修改此账号")

    updates = []
    params = []
    if account.xianyu_name is not None:
        updates.append("xianyu_name = ?")
        params.append(account.xianyu_name)
    if account.cookie is not None:
        updates.append("cookie = ?")
        params.append(account.cookie)
    if account.user_agent is not None:
        updates.append("user_agent = ?")
        params.append(account.user_agent)

    if updates:
        params.append(account_id)
        cursor.execute(
            f"UPDATE xianyu_accounts SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        conn.commit()

    # 获取更新后的数据
    cursor.execute(
        "SELECT id, user_id, xianyu_name, cookie, user_agent FROM xianyu_accounts WHERE id = ?",
        (account_id,),
    )
    row = cursor.fetchone()
    conn.close()

    data = dict(row)
    data.setdefault("user_agent", "")
    updated_account = XianyuAccount(**data)

    # 更新缓存（不自动重启客户端）
    if AccountContext.is_initialized():
        AccountContext.update_account(updated_account)

    acc_dict = updated_account.model_dump()
    acc_dict["is_active"] = AccountContext.is_account_active(account_id)
    return acc_dict


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除账号"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id FROM xianyu_accounts WHERE id = ?",
        (account_id,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="账号不存在")

    # 权限校验
    if row["user_id"] != current_user.user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="无权限删除此账号")

    cursor.execute("DELETE FROM xianyu_accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()

    # 从缓存中移除并停止客户端
    if AccountContext.is_initialized():
        asyncio.create_task(AccountContext.remove_account(account_id))

    return {"msg": "账号已删除"}


@router.post("/{account_id}/start")
async def start_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """启动指定账号的WebSocket客户端"""
    if not AccountContext.is_initialized():
        raise HTTPException(status_code=400, detail="AccountContext not initialized")

    account = AccountContext.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 权限校验
    if account.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权限操作此账号")

    success = await AccountContext.start_account(account_id)
    if success:
        return {"msg": f"账号 {account_id} 启动成功", "is_active": True}
    else:
        raise HTTPException(status_code=500, detail="启动账号失败")


@router.post("/{account_id}/stop")
async def stop_account(
    account_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """停止指定账号的WebSocket客户端"""
    if not AccountContext.is_initialized():
        raise HTTPException(status_code=400, detail="AccountContext not initialized")

    account = AccountContext.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 权限校验
    if account.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权限操作此账号")

    success = await AccountContext.stop_account(account_id)
    if success:
        return {"msg": f"账号 {account_id} 已停止", "is_active": False}
    else:
        raise HTTPException(status_code=500, detail="停止账号失败")
