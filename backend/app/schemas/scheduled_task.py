"""
定时任务相关的Pydantic模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.schemas.alert import AlertContactResponse, AlertGroupResponse


class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求"""
    name: str = Field(..., min_length=1, max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    script_id: int = Field(..., description="脚本ID")
    server_id: int = Field(..., description="服务器ID")
    cron_expression: str = Field(..., description="Cron表达式")
    enabled: bool = Field(True, description="是否启用")
    contact_ids: List[int] = Field(default_factory=list, description="通知对象ID列表")
    group_ids: List[int] = Field(default_factory=list, description="通知组ID列表")
    notify_on_success: bool = Field(False, description="成功时发送通知")
    notify_on_failure: bool = Field(False, description="失败时发送通知")

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """验证Cron表达式格式"""
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError('Cron表达式必须包含5个部分：分 时 日 月 周')
        return v


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    script_id: Optional[int] = Field(None, description="脚本ID")
    server_id: Optional[int] = Field(None, description="服务器ID")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    enabled: Optional[bool] = Field(None, description="是否启用")
    contact_ids: Optional[List[int]] = Field(None, description="通知对象ID列表")
    group_ids: Optional[List[int]] = Field(None, description="通知组ID列表")
    notify_on_success: Optional[bool] = Field(None, description="成功时发送通知")
    notify_on_failure: Optional[bool] = Field(None, description="失败时发送通知")

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """验证Cron表达式格式"""
        if v is not None:
            parts = v.strip().split()
            if len(parts) != 5:
                raise ValueError('Cron表达式必须包含5个部分：分 时 日 月 周')
        return v


class ScheduledTaskResponse(BaseModel):
    """定时任务响应"""
    id: int
    name: str
    description: Optional[str]
    script_id: int
    server_id: int
    cron_expression: str
    enabled: bool
    notify_on_success: bool
    notify_on_failure: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    contacts: List[AlertContactResponse] = Field(default_factory=list)
    groups: List[AlertGroupResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ScheduledTaskListItem(BaseModel):
    """定时任务列表项"""
    id: int
    name: str
    description: Optional[str]
    script_id: int
    server_id: int
    cron_expression: str
    enabled: bool
    notify_on_success: bool
    notify_on_failure: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    created_at: datetime
    contacts: List[AlertContactResponse] = Field(default_factory=list)
    groups: List[AlertGroupResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ScheduledTaskListResponse(BaseModel):
    """定时任务列表响应"""
    items: list[ScheduledTaskListItem]
    total: int
