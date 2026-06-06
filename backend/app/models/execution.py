"""
执行历史模型
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class ExecutionHistory(Base):
    """执行历史表模型"""
    __tablename__ = "execution_history"

    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    status = Column(String(20), nullable=False)  # 'success', 'failed', 'timeout', 'running'
    return_code = Column(Integer)
    stdout = Column(Text)
    stderr = Column(Text)
    duration_seconds = Column(Float)
    execution_type = Column(String(20), default='manual')  # 'manual', 'scheduled'
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<ExecutionHistory(id={self.id}, script_id={self.script_id}, server_id={self.server_id}, status='{self.status}')>"

    def to_dict(self, include_output=True):
        """
        转换为字典
        
        Args:
            include_output: 是否包含输出内容（列表查询时可能不需要）
        """
        data = {
            "id": self.id,
            "script_id": self.script_id,
            "server_id": self.server_id,
            "status": self.status,
            "exit_code": self.return_code,  # 前端使用exit_code
            "duration_seconds": self.duration_seconds,
            "execution_type": self.execution_type,
            "started_at": self.executed_at.isoformat() if self.executed_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None
        }
        
        if include_output:
            data["output"] = self.stdout  # 前端使用output
            data["error"] = self.stderr  # 前端使用error
        
        return data
