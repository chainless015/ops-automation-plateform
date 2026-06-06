"""
监控相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.server import Server
from app.services.prometheus_service import prometheus_service
from app.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/server/{server_id}")
async def get_server_monitoring(
    server_id: int,
    duration: str = Query("1h", description="时间范围: 1h, 24h, 7d"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取服务器所有监控数据（CPU、内存、磁盘）"""
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    try:
        instance = f"{server.ip_address}:9100"
        has_exporter = await prometheus_service.check_instance_exists(instance)

        if not has_exporter:
            return {
                "server_id": server_id,
                "server_ip": server.ip_address,
                "has_exporter": False,
                "cpu": [],
                "memory": [],
                "disk": []
            }

        cpu_result = await prometheus_service.get_cpu_usage(instance, duration)
        memory_result = await prometheus_service.get_memory_usage(instance, duration)
        disk_result = await prometheus_service.get_disk_usage(instance, duration)

        return {
            "server_id": server_id,
            "server_ip": server.ip_address,
            "has_exporter": True,
            "cpu": cpu_result["data"] if cpu_result else [],
            "memory": memory_result["data"] if memory_result else [],
            "disk": disk_result["data"] if disk_result else []
        }

    except Exception as e:
        logger.error(f"Error fetching monitoring data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching monitoring data: {str(e)}"
        )
