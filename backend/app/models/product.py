from pydantic import BaseModel
from typing import Optional


class ProductSyncRequest(BaseModel):
    """同步商品请求"""
    xianyu_account_id: int


class ProductUpdatePrompt(BaseModel):
    """更新商品主提示词"""
    main_prompt: str


class Product(BaseModel):
    """商品模型"""
    id: int
    xianyu_account_id: int
    xianyu_name: str = ""
    item_id: str = ""
    title: str = ""
    description: str = ""
    images: str = ""  # JSON array string
    skus: str = ""    # JSON array string
    main_prompt: str = ""
    price: str = ""   # 商品价格

    def get_images_list(self) -> list:
        """获取图片列表"""
        import json
        try:
            return json.loads(self.images) if self.images else []
        except:
            return []

    def get_skus_list(self) -> list:
        """获取SKU列表"""
        import json
        try:
            return json.loads(self.skus) if self.skus else []
        except:
            return []
