from fastapi import APIRouter, HTTPException, Depends

from ..database import get_db_connection
from ..models.product import (
    ProductSyncRequest,
    ProductUpdatePrompt,
    Product,
)
from ..utils.auth import get_current_user, CurrentUser

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[Product])
async def list_products(
    xianyu_account_id: int | None = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取商品列表（只返回当前用户账号下的商品）"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 子查询：获取当前用户的所有账号ID
    if xianyu_account_id:
        # 单个账号时，先校验权限
        cursor.execute(
            "SELECT user_id FROM xianyu_accounts WHERE id = ?",
            (xianyu_account_id,),
        )
        row = cursor.fetchone()
        if row is None:
            conn.close()
            raise HTTPException(status_code=404, detail="账号不存在")
        if row["user_id"] != current_user.user_id:
            conn.close()
            raise HTTPException(status_code=403, detail="无权限访问此账号")
        cursor.execute(
            """
            SELECT p.id, p.xianyu_account_id, a.xianyu_name,
                   p.item_id, p.title, p.description, p.images, p.skus, p.main_prompt
            FROM products p
            LEFT JOIN xianyu_accounts a ON p.xianyu_account_id = a.id
            WHERE p.xianyu_account_id = ?
            """,
            (xianyu_account_id,),
        )
    else:
        # 获取当前用户所有账号的商品
        cursor.execute(
            """
            SELECT p.id, p.xianyu_account_id, a.xianyu_name,
                   p.item_id, p.title, p.description, p.images, p.skus, p.main_prompt
            FROM products p
            LEFT JOIN xianyu_accounts a ON p.xianyu_account_id = a.id
            WHERE a.user_id = ?
            """,
            (current_user.user_id,),
        )

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """获取单个商品"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.xianyu_account_id, a.xianyu_name,
               p.item_id, p.title, p.description, p.images, p.skus, p.main_prompt
        FROM products p
        LEFT JOIN xianyu_accounts a ON p.xianyu_account_id = a.id
        WHERE p.id = ?
        """,
        (product_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 权限校验
    cursor2 = conn.cursor() if conn.closed else None
    conn2 = get_db_connection()
    cursor2 = conn2.cursor()
    cursor2.execute(
        "SELECT user_id FROM xianyu_accounts WHERE id = ?",
        (row["xianyu_account_id"],),
    )
    account_row = cursor2.fetchone()
    conn2.close()

    if account_row is None or account_row["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权限访问此商品")

    return dict(row)


@router.put("/{product_id}/prompt", response_model=Product)
async def update_product_prompt(
    product_id: int,
    update: ProductUpdatePrompt,
    current_user: CurrentUser = Depends(get_current_user),
):
    """更新商品主提示词"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先获取商品信息校验权限
    cursor.execute(
        """
        SELECT p.id, p.xianyu_account_id
        FROM products p
        LEFT JOIN xianyu_accounts a ON p.xianyu_account_id = a.id
        WHERE p.id = ?
        """,
        (product_id,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="商品不存在")

    # 权限校验
    cursor.execute(
        "SELECT user_id FROM xianyu_accounts WHERE id = ?",
        (row["xianyu_account_id"],),
    )
    account_row = cursor.fetchone()
    if account_row is None or account_row["user_id"] != current_user.user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="无权限修改此商品")

    cursor.execute(
        "UPDATE products SET main_prompt = ? WHERE id = ?",
        (update.main_prompt, product_id),
    )
    conn.commit()
    conn.close()

    return await get_product(product_id, current_user)


@router.post("/sync")
async def sync_product(
    request: ProductSyncRequest,
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    同步商品信息
    TODO: 实现从闲鱼API获取商品信息
    """
    # 校验账号权限
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM xianyu_accounts WHERE id = ?",
        (request.xianyu_account_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    if row["user_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="无权限操作此账号")

    return {"msg": "同步功能待实现"}


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
):
    """删除商品"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 先获取商品信息校验权限
    cursor.execute(
        """
        SELECT p.id, p.xianyu_account_id
        FROM products p
        LEFT JOIN xianyu_accounts a ON p.xianyu_account_id = a.id
        WHERE p.id = ?
        """,
        (product_id,),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="商品不存在")

    # 权限校验
    cursor.execute(
        "SELECT user_id FROM xianyu_accounts WHERE id = ?",
        (row["xianyu_account_id"],),
    )
    account_row = cursor.fetchone()
    if account_row is None or account_row["user_id"] != current_user.user_id:
        conn.close()
        raise HTTPException(status_code=403, detail="无权限删除此商品")

    cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"msg": "商品已删除"}
