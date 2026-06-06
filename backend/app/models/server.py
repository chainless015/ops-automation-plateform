"""
服务器模型
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class Server(Base):
    """服务器表模型"""
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(100), nullable=False)
    ip_address = Column(String(45), unique=True, nullable=False, index=True)
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(50))
    ssh_password = Column(String(255))  # 加密存储
    purpose = Column(String(200))
    owner = Column(String(50))
    status = Column(String(20), default="online", index=True)  # 'online', 'offline'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Server(id={self.id}, hostname='{self.hostname}', ip='{self.ip_address}')>"

    def to_dict(self, include_password=False):
        """
        转换为字典
        
        Args:
            include_password: 是否包含SSH密码（默认不包含）
        """
        data = {
            "id": self.id,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "ssh_port": self.ssh_port,
            "ssh_username": self.ssh_username,
            "purpose": self.purpose,
            "owner": self.owner,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_password:
            data["ssh_password"] = self.ssh_password
        
        return data
