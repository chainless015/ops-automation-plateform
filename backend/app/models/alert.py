"""
告警相关模型
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AlertStatus(str, enum.Enum):
    """告警状态"""
    FIRING = "firing"    # 触发中
    RESOLVED = "resolved"  # 已解决


def _enum_values(enum_cls):
    """SQLAlchemy Enum 默认存成员名，需显式指定存 value 以匹配数据库 CHECK 约束"""
    return [member.value for member in enum_cls]


class AlertSeverity(str, enum.Enum):
    """告警级别（4级最高，1级最低）"""
    LEVEL1 = "level1"  # 1级告警（最低）
    LEVEL2 = "level2"  # 2级告警
    LEVEL3 = "level3"  # 3级告警
    LEVEL4 = "level4"  # 4级告警（最高）


class AlertContact(Base):
    """告警人表"""
    __tablename__ = "alert_contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(20))
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AlertGroup(Base):
    """告警组表"""
    __tablename__ = "alert_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AlertGroupMember(Base):
    """告警组成员关联表"""
    __tablename__ = "alert_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("alert_groups.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("alert_contacts.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertRule(Base):
    """告警规则表"""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"))
    metric_type = Column(String(50), nullable=False)  # cpu, memory, disk_mount, tcp_conn, host_up
    metric_label = Column(String(255))  # 指标标签，如挂载点 "/data" 或 TCP 状态
    operator = Column(String(10), nullable=False)  # >, <, >=, <=, ==
    threshold = Column(Float, nullable=False)
    duration = Column(Integer, default=5)  # 持续时间（分钟）
    repeat_interval = Column(Integer, default=30)  # 重发间隔（分钟）
    severity = Column(SQLEnum(AlertSeverity, values_callable=_enum_values), default=AlertSeverity.LEVEL3)
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "server_id": self.server_id,
            "metric_type": self.metric_type,
            "metric_label": self.metric_label,
            "operator": self.operator,
            "threshold": self.threshold,
            "duration": self.duration,
            "repeat_interval": self.repeat_interval,
            "severity": self.severity.value if self.severity else None,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class AlertRuleNotification(Base):
    """告警规则通知配置表"""
    __tablename__ = "alert_rule_notifications"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("alert_contacts.id", ondelete="CASCADE"))
    group_id = Column(Integer, ForeignKey("alert_groups.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Alert(Base):
    """告警记录表"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="SET NULL"))
    rule_name = Column(String(100))  # 触发时快照，规则删除后仍可追溯
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"))
    metric_type = Column(String(50), nullable=False)
    metric_label = Column(String(255))  # 指标标签，如挂载点或TCP连接类型
    current_value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    operator = Column(String(10))  # 触发时快照
    severity = Column(SQLEnum(AlertSeverity, values_callable=_enum_values), default=AlertSeverity.LEVEL3)
    status = Column(SQLEnum(AlertStatus, values_callable=_enum_values), default=AlertStatus.FIRING, index=True)
    fired_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)  # 首次触发时间
    last_occurred_at = Column(DateTime(timezone=True), index=True)  # 最后发生时间
    resolved_at = Column(DateTime(timezone=True))
    last_notified_at = Column(DateTime(timezone=True))  # 上次通知时间

    def to_dict(self):
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "server_id": self.server_id,
            "metric_type": self.metric_type,
            "metric_label": self.metric_label,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "operator": self.operator,
            "severity": self.severity.value if self.severity else None,
            "status": self.status.value if self.status else None,
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "last_occurred_at": self.last_occurred_at.isoformat() if self.last_occurred_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "last_notified_at": self.last_notified_at.isoformat() if self.last_notified_at else None
        }


class AlertSilence(Base):
    """告警屏蔽表"""
    __tablename__ = "alert_silences"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"))
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"))
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"))
    reason = Column(Text)
    silenced_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "server_id": self.server_id,
            "reason": self.reason,
            "silenced_at": self.silenced_at.isoformat() if self.silenced_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active
        }
