"""
脚本相关的Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ScriptCreate(BaseModel):
    """创建脚本请求"""
    name: str = Field(..., min_length=1, max_length=100, description="脚本名称")
    description: Optional[str] = Field(None, description="脚本描述")
    content: str = Field(..., min_length=1, description="脚本内容")

    @validator("name")
    def validate_name(cls, v):
        """验证脚本名称必须以.sh结尾"""
        if not v.endswith(".sh"):
            raise ValueError("Script name must end with .sh")
        return v


class ScriptUpdate(BaseModel):
    """更新脚本请求"""
    description: Optional[str] = None
    content: Optional[str] = Field(None, min_length=1)


class ScriptResponse(BaseModel):
    """脚本响应"""
    id: int
    name: str
    description: Optional[str]
    content: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScriptListItem(BaseModel):
    """脚本列表项（不包含内容）"""
    id: int
    name: str
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScriptListResponse(BaseModel):
    """脚本列表响应（带分页信息）"""
    items: list[ScriptListItem]
    total: int
