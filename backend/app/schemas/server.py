"""
服务器相关的Pydantic模型
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import ipaddress


class ServerCreate(BaseModel):
    """创建服务器请求"""
    hostname: str = Field(..., min_length=1, max_length=100, description="主机名")
    ip_address: str = Field(..., description="IP地址")
    ssh_port: int = Field(default=22, ge=1, le=65535, description="SSH端口")
    ssh_username: Optional[str] = Field(None, max_length=50, description="SSH用户名")
    ssh_password: Optional[str] = Field(None, description="SSH密码")
    purpose: Optional[str] = Field(None, max_length=200, description="服务器用途")
    owner: Optional[str] = Field(None, max_length=50, description="负责人")

    @validator("ip_address")
    def validate_ip(cls, v):
        """验证IP地址格式"""
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class ServerUpdate(BaseModel):
    """更新服务器请求"""
    hostname: Optional[str] = Field(None, min_length=1, max_length=100)
    ssh_port: Optional[int] = Field(None, ge=1, le=65535)
    ssh_username: Optional[str] = Field(None, max_length=50)
    ssh_password: Optional[str] = None
    purpose: Optional[str] = Field(None, max_length=200)
    owner: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = None

    @validator("status")
    def validate_status(cls, v):
        """验证状态值"""
        if v is not None:
            allowed_statuses = ["online", "offline"]
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v


class ServerResponse(BaseModel):
    """服务器响应"""
    id: int
    hostname: str
    ip_address: str
    ssh_port: int
    ssh_username: Optional[str]
    purpose: Optional[str]
    owner: Optional[str]
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ServerListResponse(BaseModel):
    """服务器列表响应"""
    total: int
    page: int
    page_size: int
    items: list[ServerResponse]


class SSHTestRequest(BaseModel):
    """SSH 连接测试请求"""
    ip_address: str = Field(..., description="IP地址")
    ssh_port: int = Field(default=22, ge=1, le=65535, description="SSH端口")
    ssh_username: str = Field(..., min_length=1, max_length=50, description="SSH用户名")
    ssh_password: Optional[str] = Field(None, description="SSH密码（编辑时留空则使用已保存密码）")
    server_id: Optional[int] = Field(None, description="服务器ID（编辑时使用已保存密码）")

    @validator("ip_address")
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError("Invalid IP address format")


class SSHTestResponse(BaseModel):
    """SSH 连接测试响应"""
    success: bool
    message: str
    duration_seconds: Optional[float] = None
