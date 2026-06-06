"""
执行历史相关的Pydantic模型
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ExecutionCreate(BaseModel):
    """执行脚本请求"""
    script_id: int
    server_id: int


class ExecutionListItem(BaseModel):
    """执行历史列表项"""
    id: int
    script_id: int
    script_name: Optional[str] = None
    server_id: int
    server_hostname: Optional[str] = None
    server_ip: Optional[str] = None
    status: str
    exit_code: Optional[int] = None
    duration_seconds: Optional[float] = None
    execution_type: str = 'manual'
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutionDetail(BaseModel):
    """执行历史详情"""
    id: int
    script_id: int
    script_name: Optional[str] = None
    server_id: int
    server_hostname: Optional[str] = None
    server_ip: Optional[str] = None
    status: str
    exit_code: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    execution_type: str = 'manual'
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExecutionResponse(BaseModel):
    """执行响应"""
    execution_id: int
    status: str
    message: str
