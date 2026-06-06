"""
服务器管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import subprocess
import platform
import shutil
import socket
from app.core.database import get_db
from app.core.security import encrypt_ssh_password
from app.models.user import User
from app.models.server import Server
from app.schemas.server import ServerCreate, ServerUpdate, ServerResponse, ServerListResponse
from app.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _tcp_check(ip_address: str, port: int = 22) -> bool:
    """通过 TCP 端口检测主机是否可达"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip_address, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.warning(f"TCP test error for {ip_address}:{port}: {e}")
        return False


def ping_server(ip_address: str) -> bool:
    """
    检测服务器是否在线：优先 ping，不可用时静默改用 SSH 端口 TCP 检测。
    """
    if ip_address in ['localhost', '127.0.0.1', '::1']:
        return True

    if not shutil.which('ping'):
        return _tcp_check(ip_address)

    try:
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
        command = ['ping', param, '1', timeout_param, '2', ip_address]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3
        )
        logger.info(f"Ping {ip_address}: return code {result.returncode}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping timeout for {ip_address}")
        return _tcp_check(ip_address)
    except Exception as e:
        logger.warning(f"Ping error for {ip_address}: {e}")
        return _tcp_check(ip_address)


@router.get("", response_model=ServerListResponse)
def get_servers(
    search: Optional[str] = Query(None, description="搜索主机名或IP地址"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取服务器列表
    
    Args:
        search: 搜索关键词（主机名或IP地址）
        status: 状态筛选
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        服务器列表
    """
    # 构建查询
    query = db.query(Server)
    
    # 搜索条件
    if search:
        query = query.filter(
            (Server.hostname.ilike(f"%{search}%")) | 
            (Server.ip_address.ilike(f"%{search}%"))
        )
    
    # 状态筛选
    if status:
        query = query.filter(Server.status == status)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    servers = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 转换为响应格式
    items = [ServerResponse(**server.to_dict()) for server in servers]
    
    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [item.model_dump() for item in items]
    }
    
    return ServerListResponse(**response_data)


@router.post("", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
def create_server(
    server_data: ServerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建服务器
    
    Args:
        server_data: 服务器数据
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        创建的服务器信息
    
    Raises:
        HTTPException: IP地址已存在时抛出409错误
    """
    # 检查IP是否已存在
    existing_server = db.query(Server).filter(Server.ip_address == server_data.ip_address).first()
    if existing_server:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Server with IP {server_data.ip_address} already exists"
        )
    
    # 加密SSH密码
    encrypted_password = None
    if server_data.ssh_password:
        encrypted_password = encrypt_ssh_password(server_data.ssh_password)
    
    # 检测服务器在线状态
    is_online = ping_server(server_data.ip_address)
    initial_status = "online" if is_online else "offline"
    
    # 创建服务器记录
    server = Server(
        hostname=server_data.hostname,
        ip_address=server_data.ip_address,
        ssh_port=server_data.ssh_port,
        ssh_username=server_data.ssh_username,
        ssh_password=encrypted_password,
        purpose=server_data.purpose,
        owner=server_data.owner,
        status=initial_status
    )
    
    db.add(server)
    db.commit()
    db.refresh(server)

    # 同步Prometheus targets
    try:
        from app.api.prometheus_targets import _sync_prometheus_targets_impl
        _sync_prometheus_targets_impl(db)
    except Exception as e:
        logger.warning(f"Failed to sync Prometheus targets: {e}")
    
    logger.info(f"User {current_user.username} created server {server.hostname} ({server.ip_address})")
    
    return ServerResponse(**server.to_dict())


@router.get("/{server_id}", response_model=ServerResponse)
def get_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取服务器详情
    
    Args:
        server_id: 服务器ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        服务器详情
    
    Raises:
        HTTPException: 服务器不存在时抛出404错误
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    return ServerResponse(**server.to_dict())


@router.put("/{server_id}", response_model=ServerResponse)
def update_server(
    server_id: int,
    server_data: ServerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新服务器信息
    
    Args:
        server_id: 服务器ID
        server_data: 更新数据
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        更新后的服务器信息
    
    Raises:
        HTTPException: 服务器不存在时抛出404错误
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    # 更新字段
    update_data = server_data.model_dump(exclude_unset=True)
    
    # 处理SSH密码加密
    if "ssh_password" in update_data and update_data["ssh_password"]:
        update_data["ssh_password"] = encrypt_ssh_password(update_data["ssh_password"])
    
    for field, value in update_data.items():
        setattr(server, field, value)
    
    db.commit()
    db.refresh(server)
    
    logger.info(f"User {current_user.username} updated server {server.hostname} ({server.ip_address})")
    
    return ServerResponse(**server.to_dict())


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_server(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除服务器
    
    Args:
        server_id: 服务器ID
        db: 数据库会话
        current_user: 当前用户
    
    Raises:
        HTTPException: 服务器不存在或有关联资源时抛出错误
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    # 删除关联的告警记录
    from app.models.alert import Alert
    db.query(Alert).filter(Alert.server_id == server_id).delete()

    # 删除关联的执行记录
    from app.models.execution import ExecutionHistory
    db.query(ExecutionHistory).filter(ExecutionHistory.server_id == server_id).delete()
    
    # 删除服务器
    db.delete(server)
    db.commit()
    
    try:
        from app.api.prometheus_targets import _sync_prometheus_targets_impl
        _sync_prometheus_targets_impl(db)
    except Exception as e:
        logger.warning(f"Failed to sync Prometheus targets: {e}")

    logger.info(f"User {current_user.username} deleted server {server.hostname} ({server.ip_address})")
    
    return None


@router.get("/{server_id}/ping")
def ping_server_status(
    server_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ping服务器检测在线状态（不更新数据库）
    
    Args:
        server_id: 服务器ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        服务器在线状态
    
    Raises:
        HTTPException: 服务器不存在时抛出404错误
    """
    server = db.query(Server).filter(Server.id == server_id).first()
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    
    # 检测服务器是否在线
    is_online = ping_server(server.ip_address)
    status_value = "online" if is_online else "offline"
    
    return {
        "server_id": server_id,
        "ip_address": server.ip_address,
        "status": status_value,
        "is_online": is_online
    }
