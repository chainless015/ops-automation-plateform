"""
仪表盘API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.core.database import get_db
from app.core.timezone import get_timezone
from app.models.user import User
from app.models.alert import Alert, AlertStatus
from app.models.execution import ExecutionHistory
from app.models.scheduled_task import ScheduledTask
from app.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取仪表盘统计数据"""
    now = datetime.now(get_timezone())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. 当前告警数（FIRING）及今日 / 昨日告警统计
    current_alerts = db.query(Alert).filter(
        Alert.status == AlertStatus.FIRING
    ).count()

    today_alerts = db.query(Alert).filter(
        Alert.fired_at >= today_start
    ).count()

    # 今日 / 昨日告警数（今日告警卡片展示）
    yesterday_start = today_start - timedelta(days=1)
    yesterday_alerts = db.query(Alert).filter(
        Alert.fired_at >= yesterday_start,
        Alert.fired_at < today_start
    ).count()

    # 2. 今日脚本执行统计
    today_executions = db.query(ExecutionHistory).filter(
        ExecutionHistory.executed_at >= today_start
    ).all()

    total_executions = len(today_executions)
    success_executions = sum(1 for e in today_executions if e.status == 'success')
    failed_executions = sum(1 for e in today_executions if e.status == 'failed')
    success_rate = round(success_executions / total_executions * 100, 1) if total_executions > 0 else None

    # 3. 活跃定时任务数（已启用）及总数
    active_scheduled_tasks = db.query(ScheduledTask).filter(ScheduledTask.enabled == True).count()
    total_scheduled_tasks = db.query(ScheduledTask).count()

    # 4. 近7天告警趋势（按天聚合）
    alert_trend = []
    for i in range(7):
        day_start = (now - timedelta(days=6 - i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = db.query(Alert).filter(
            and_(Alert.fired_at >= day_start, Alert.fired_at < day_end)
        ).count()
        alert_trend.append({
            "date": day_start.strftime("%m-%d"),
            "count": count
        })

    # 5. 告警级别分布（近7天）
    seven_days_ago = now - timedelta(days=7)
    severity_distribution = db.query(
        Alert.severity,
        func.count(Alert.id).label('count')
    ).filter(
        Alert.fired_at >= seven_days_ago
    ).group_by(Alert.severity).all()

    severity_stats = {"level1": 0, "level2": 0, "level3": 0, "level4": 0}
    for severity, count in severity_distribution:
        severity_key = severity.value if hasattr(severity, 'value') else severity
        if severity_key in severity_stats:
            severity_stats[severity_key] = count

    return {
        "current_alerts": current_alerts,
        "today_alerts": today_alerts,
        "yesterday_alerts": yesterday_alerts,
        "executions": {
            "total": total_executions,
            "success": success_executions,
            "failed": failed_executions,
            "success_rate": success_rate
        },
        "scheduled_tasks": {
            "active": active_scheduled_tasks,
            "total": total_scheduled_tasks
        },
        "alert_trend": alert_trend,
        "severity_distribution": severity_stats
    }


@router.get("/recent-executions")
def get_recent_executions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取最近的执行记录
    
    Returns:
        最近5条执行记录
    """
    executions = db.query(ExecutionHistory).order_by(
        ExecutionHistory.executed_at.desc()
    ).limit(5).all()
    
    return [execution.to_dict(include_output=False) for execution in executions]


@router.get("/top-servers")
async def get_top_servers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取资源使用率最高的服务器
    
    Returns:
        Top 5 服务器及其资源使用情况
    """
    from app.models.server import Server
    from app.services.prometheus_service import prometheus_service
    
    # 获取所有活跃服务器
    servers = db.query(Server).filter(Server.status == 'online').all()
    logger.info(f"Found {len(servers)} online servers")
    
    server_metrics = []
    for server in servers:
        try:
            # 构建instance标识（IP:端口）
            instance = f"{server.ip_address}:9100"
            logger.info(f"Fetching metrics for server {server.hostname} ({instance})")
            
            # 检查实例是否存在
            instance_exists = await prometheus_service.check_instance_exists(instance)
            if not instance_exists:
                logger.warning(f"Instance {instance} not found in Prometheus")
                continue
            
            # 获取当前指标（使用短时间范围获取最新值）
            metrics = await prometheus_service.get_all_metrics(instance, duration="5m")
            
            if metrics:
                cpu_data = metrics.get("cpu")
                memory_data = metrics.get("memory")
                disk_data = metrics.get("disk")
                
                # 检查是否有有效数据
                if not cpu_data or not memory_data or not disk_data:
                    logger.warning(f"Incomplete metrics for server {server.hostname}: cpu={cpu_data is not None}, memory={memory_data is not None}, disk={disk_data is not None}")
                    continue
                
                cpu_current = cpu_data.get("statistics", {}).get("current", 0) if cpu_data else 0
                memory_current = memory_data.get("statistics", {}).get("current", 0) if memory_data else 0
                disk_current = disk_data.get("statistics", {}).get("current", 0) if disk_data else 0
                
                logger.info(f"Server {server.hostname} metrics - CPU: {cpu_current}%, Memory: {memory_current}%, Disk: {disk_current}%")
                
                server_metrics.append({
                    "id": server.id,
                    "hostname": server.hostname,
                    "ip_address": server.ip_address,
                    "cpu_usage": round(cpu_current, 2),
                    "memory_usage": round(memory_current, 2),
                    "disk_usage": round(disk_current, 2)
                })
            else:
                logger.warning(f"No metrics returned for server {server.hostname}")
        except Exception as e:
            logger.error(f"Failed to get metrics for server {server.hostname}: {str(e)}", exc_info=True)
            continue
    
    # 按CPU使用率排序，取前5
    server_metrics.sort(key=lambda x: x["cpu_usage"], reverse=True)
    result = server_metrics[:5]
    
    logger.info(f"Returning {len(result)} servers with metrics")
    return result
