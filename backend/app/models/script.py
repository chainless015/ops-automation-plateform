"""
脚本模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Script(Base):
    """脚本表模型"""
    __tablename__ = "scripts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Script(id={self.id}, name='{self.name}')>"

    def to_dict(self, include_content=True):
        """
        转换为字典
        
        Args:
            include_content: 是否包含脚本内容（列表查询时可能不需要）
        """
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_content:
            data["content"] = self.content
        
        return data
