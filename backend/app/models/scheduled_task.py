"""
定时任务模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class ScheduledTask(Base):
    """定时任务表模型"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    script_id = Column(Integer, ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=False)
    last_run_at = Column(DateTime(timezone=True))
    last_run_status = Column(String(20))
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, name='{self.name}', enabled={self.enabled})>"

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "script_id": self.script_id,
            "server_id": self.server_id,
            "cron_expression": self.cron_expression,
            "enabled": self.enabled,
            "notify_on_success": self.notify_on_success,
            "notify_on_failure": self.notify_on_failure,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ScheduledTaskNotification(Base):
    """定时任务通知配置"""
    __tablename__ = "scheduled_task_notifications"
    __table_args__ = (
        CheckConstraint(
            "(contact_id IS NOT NULL) OR (group_id IS NOT NULL)",
            name="scheduled_task_notifications_target_check"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("scheduled_tasks.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("alert_contacts.id", ondelete="CASCADE"))
    group_id = Column(Integer, ForeignKey("alert_groups.id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
