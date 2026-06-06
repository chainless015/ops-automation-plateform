"""
Prometheus Targets管理API - 动态添加/删除监控目标
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.server import Server
from app.utils.dependencies import get_current_user
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Prometheus targets文件路径
TARGETS_FILE = "/app/prometheus/targets/servers.json"


def read_targets():
    """读取targets配置"""
    try:
        if os.path.exists(TARGETS_FILE):
            with open(TARGETS_FILE, 'r') as f:
                content = f.read()
                if not content.strip():
                    logger.warning("Targets file is empty")
                    return []
                return json.loads(content)
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in targets file: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading targets file: {e}")
        return []


def write_targets(targets):
    """写入targets配置"""
    try:
        os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
        
        # 使用原子写入：先写临时文件，再重命名
        temp_file = TARGETS_FILE + ".tmp"
        
        with open(temp_file, 'w') as f:
            json.dump(targets, f, indent=2)
        
        # 原子重命名操作
        os.replace(temp_file, TARGETS_FILE)
        
        # 设置文件权限为644（所有人可读）
        os.chmod(TARGETS_FILE, 0o644)
        logger.info(f"Updated Prometheus targets: {len(targets)} targets")
        return True
    except Exception as e:
        logger.error(f"Error writing targets file: {e}")
        # 清理临时文件
        temp_file = TARGETS_FILE + ".tmp"
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        return False


@router.post("/sync")
def sync_prometheus_targets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    同步所有服务器到Prometheus targets
    从数据库读取所有服务器，更新Prometheus配置
    """
    return _sync_prometheus_targets_impl(db)


def _sync_prometheus_targets_impl(db: Session):
    """
    同步所有服务器到Prometheus targets的实现函数
    从数据库读取所有服务器，更新Prometheus配置
    """
    try:
        # 获取所有服务器
        servers = db.query(Server).all()
        logger.info(f"Syncing {len(servers)} servers to Prometheus targets")
        
        # 构建targets列表
        targets = []
        for server in servers:
            # 使用服务器IP作为target
            target = {
                "targets": [f"{server.ip_address}:9100"],
                "labels": {
                    "server_ip": server.ip_address,
                    "hostname": server.hostname
                }
            }
            targets.append(target)
            logger.debug(f"Added target: {server.ip_address}:9100 ({server.hostname})")
        
        # 写入文件
        if write_targets(targets):
            logger.info(f"Successfully synced {len(targets)} servers to Prometheus")
            return {
                "success": True,
                "message": f"Successfully synced {len(targets)} servers to Prometheus",
                "targets_count": len(targets)
            }
        else:
            logger.error("Failed to write targets file")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to write targets file"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing targets: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
