"""
告警相关的Pydantic模型
"""
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from typing import List, Optional
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    """告警级别"""
    LEVEL1 = "level1"
    LEVEL2 = "level2"
    LEVEL3 = "level3"
    LEVEL4 = "level4"


# ===== 告警人 =====
class AlertContactCreate(BaseModel):
    """创建告警人"""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    enabled: bool = True


class AlertContactUpdate(BaseModel):
    """更新告警人"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    enabled: Optional[bool] = None


class AlertContactResponse(BaseModel):
    """告警人响应"""
    id: int
    name: str
    email: str
    phone: Optional[str]
    enabled: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===== 告警组 =====
class AlertGroupCreate(BaseModel):
    """创建告警组"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    contact_ids: List[int] = Field(default_factory=list)


class AlertGroupUpdate(BaseModel):
    """更新告警组"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    contact_ids: Optional[List[int]] = None


class AlertGroupResponse(BaseModel):
    """告警组响应"""
    id: int
    name: str
    description: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    contacts: List[AlertContactResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ===== 告警规则 =====
class AlertRuleCreate(BaseModel):
    """创建告警规则"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    server_id: int
    metric_type: str = Field(..., description="cpu, memory, disk_mount, tcp_conn, host_up")
    metric_label: Optional[str] = Field(None, description="指标标签，如挂载点 '/data' 或 TCP 类型")
    operator: str = Field(..., description=">, <, >=, <=, ==")
    threshold: float = Field(..., ge=0)
    duration: int = Field(default=5, ge=1, le=1440, description="持续时间（分钟）")
    repeat_interval: int = Field(default=30, ge=1, le=1440, description="重发间隔（分钟）")
    severity: AlertSeverity = AlertSeverity.LEVEL3
    enabled: bool = True
    contact_ids: List[int] = Field(default_factory=list)
    group_ids: List[int] = Field(default_factory=list)

    @field_validator("metric_type")
    @classmethod
    def validate_metric_type(cls, v):
        allowed = ["cpu", "memory", "disk_mount", "tcp_conn", "host_up"]
        if v not in allowed:
            raise ValueError(f"metric_type must be one of: {', '.join(allowed)}")
        return v

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        allowed = [">", "<", ">=", "<=", "=="]
        if v not in allowed:
            raise ValueError(f"operator must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator("metric_label")
    @classmethod
    def validate_metric_label(cls, v, info):
        metric_type = info.data.get("metric_type")
        if metric_type == "disk_mount" and not v:
            raise ValueError("metric_label is required for disk_mount metric type")
        if metric_type == "tcp_conn" and not v:
            raise ValueError("metric_label is required for tcp_conn metric type")
        return v

    @model_validator(mode="after")
    def apply_host_up_fixed_condition(self):
        if self.metric_type == "host_up":
            self.operator = "<"
            self.threshold = 1
            self.metric_label = None
        return self


class AlertRuleUpdate(BaseModel):
    """更新告警规则"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    metric_label: Optional[str] = None
    threshold: Optional[float] = Field(None, ge=0)
    duration: Optional[int] = Field(None, ge=1, le=1440)
    repeat_interval: Optional[int] = Field(None, ge=1, le=1440)
    severity: Optional[AlertSeverity] = None
    enabled: Optional[bool] = None
    contact_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None


class AlertRuleResponse(BaseModel):
    """告警规则响应"""
    id: int
    name: str
    description: Optional[str]
    server_id: int
    metric_type: str
    metric_label: Optional[str]
    operator: str
    threshold: float
    duration: int
    repeat_interval: int
    severity: str
    enabled: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    contacts: List[AlertContactResponse] = Field(default_factory=list)
    groups: List[AlertGroupResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ===== 告警记录 =====
class AlertResponse(BaseModel):
    """告警记录响应"""
    id: int
    rule_id: Optional[int]
    rule_name: Optional[str] = None
    server_id: int
    metric_type: str
    metric_label: Optional[str]
    current_value: float
    threshold: float
    operator: Optional[str] = None
    severity: str
    status: str
    fired_at: Optional[datetime]
    last_occurred_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """告警列表响应"""
    total: int
    page: int
    page_size: int
    items: List[AlertResponse]


# ===== 告警屏蔽 =====
class AlertSilenceCreate(BaseModel):
    """创建告警屏蔽"""
    alert_id: Optional[int] = None
    rule_id: Optional[int] = None
    server_id: Optional[int] = None
    reason: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, description="屏蔽时长（分钟）")
    expires_at: Optional[datetime] = Field(None, description="屏蔽到期时间")

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(cls, v, info):
        if v is None and info.data.get("duration_minutes") is None:
            raise ValueError("duration_minutes or expires_at must be provided")
        return v


class AlertSilenceResponse(BaseModel):
    """告警屏蔽响应"""
    id: int
    alert_id: Optional[int]
    rule_id: Optional[int]
    server_id: Optional[int]
    reason: Optional[str]
    silenced_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
