"""
告警检查服务 - 定期检查告警规则并触发告警
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.timezone import get_timezone
from app.models.alert import AlertRule, Alert, AlertStatus, AlertSilence
from app.models.server import Server
from app.services.prometheus_service import prometheus_service
from app.services.notification_service import notification_service
import logging

logger = logging.getLogger(__name__)


class AlertCheckerService:
    """告警检查服务"""
    
    def __init__(self):
        self.check_interval = 60  # 检查间隔（秒）
        self.running = False
    
    async def start(self):
        """启动告警检查服务"""
        self.running = True
        logger.info("Alert checker service started")
        
        while self.running:
            try:
                await self.check_all_rules()
            except Exception as e:
                logger.error(f"Error in alert checker: {e}")
            
            # 等待下一次检查
            await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """停止告警检查服务"""
        self.running = False
        logger.info("Alert checker service stopped")
    
    async def check_all_rules(self):
        """检查所有启用的告警规则"""
        db = SessionLocal()
        try:
            # 清理过期的屏蔽
            self.cleanup_expired_silences(db)
            
            # 清理已禁用规则相关的告警
            self.cleanup_disabled_rules_alerts(db)
            
            # 获取所有启用的告警规则
            rules = db.query(AlertRule).filter(AlertRule.enabled == True).all()
            
            # 按服务器和指标类型分组，然后按严重级别排序（高优先级先检查）
            rules_by_metric = {}
            for rule in rules:
                key = (rule.server_id, rule.metric_type, rule.metric_label)
                if key not in rules_by_metric:
                    rules_by_metric[key] = []
                rules_by_metric[key].append(rule)
            
            # 对每个指标的规则按严重级别排序（4级最高，1级最低）
            severity_order = {"level4": 0, "level3": 1, "level2": 2, "level1": 3}
            for rules_list in rules_by_metric.values():
                rules_list.sort(
                    key=lambda r: severity_order.get(
                        r.severity.value if hasattr(r.severity, 'value') else r.severity,
                        999
                    )
                )
            
            # 记录已触发的指标，用于抑制低级别告警
            triggered_metrics = set()
            
            # 检查所有规则，高优先级规则优先
            for rules_list in rules_by_metric.values():
                for rule in rules_list:
                    try:
                        metric_key = (rule.server_id, rule.metric_type, rule.metric_label)
                        
                        # 检查该指标是否已有高优先级告警触发
                        if metric_key in triggered_metrics:
                            logger.debug(f"Rule {rule.id} suppressed: higher priority alert already triggered for this metric")
                            continue
                        
                        # 检查规则
                        await self.check_rule(db, rule)
                        
                        # 如果规则触发了告警，标记该指标为已触发
                        existing_alert = db.query(Alert).filter(
                            Alert.rule_id == rule.id,
                            Alert.server_id == rule.server_id,
                            Alert.status == AlertStatus.FIRING
                        ).first()
                        
                        if existing_alert:
                            triggered_metrics.add(metric_key)
                    except Exception as e:
                        logger.error(f"Error checking rule {rule.id}: {e}")
            
            db.commit()
        except Exception as e:
            logger.error(f"Error in check_all_rules: {e}")
            db.rollback()
        finally:
            db.close()
    
    def cleanup_expired_silences(self, db: Session):
        """清理过期的屏蔽记录"""
        now = datetime.now(get_timezone())
        
        # 将过期的屏蔽标记为不活跃
        expired_silences = db.query(AlertSilence).filter(
            AlertSilence.is_active == True,
            AlertSilence.expires_at <= now
        ).all()
        
        for silence in expired_silences:
            silence.is_active = False
            logger.info(f"Silence {silence.id} expired and deactivated")
        
        if expired_silences:
            db.commit()
    
    def cleanup_disabled_rules_alerts(self, db: Session):
        """清理已禁用规则相关的活跃告警"""
        # 查找所有已禁用的规则
        disabled_rules = db.query(AlertRule).filter(AlertRule.enabled == False).all()
        
        for rule in disabled_rules:
            # 找到该规则相关的 FIRING 告警
            active_alerts = db.query(Alert).filter(
                Alert.rule_id == rule.id,
                Alert.status == AlertStatus.FIRING
            ).all()
            
            if active_alerts:
                for alert in active_alerts:
                    alert.status = AlertStatus.RESOLVED
                    alert.resolved_at = datetime.now(get_timezone())
                    logger.info(f"Alert {alert.id} auto-resolved: associated rule {rule.id} is disabled")
                
                db.commit()
    
    async def check_rule(self, db: Session, rule: AlertRule):
        """检查单个告警规则"""
        # 检查规则是否被禁用
        if not rule.enabled:
            logger.debug(f"Rule {rule.id} is disabled, resolving any active alerts")
            # 将该规则相关的 FIRING 告警设为 RESOLVED
            active_alerts = db.query(Alert).filter(
                Alert.rule_id == rule.id,
                Alert.status == AlertStatus.FIRING
            ).all()
            
            for alert in active_alerts:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now(get_timezone())
                logger.info(f"Alert {alert.id} auto-resolved: rule {rule.name} is disabled")
            return
        
        # 获取服务器信息
        server = db.query(Server).filter(Server.id == rule.server_id).first()
        if not server:
            logger.warning(f"Server {rule.server_id} not found for rule {rule.id}")
            return
        
        # 检查是否被屏蔽（仅用于跳过通知，不影响告警创建/更新）
        is_silenced = self.is_silenced(db, rule.id, rule.server_id)
        
        # 获取监控数据
        current_value = await self.get_metric_value(server.ip_address, rule.metric_type, rule.metric_label)
        if current_value is None:
            logger.warning(f"Failed to get metric {rule.metric_type} for server {server.id}")
            return
        
        # 检查是否触发告警
        is_triggered = self.evaluate_condition(current_value, rule.operator, rule.threshold)
        
        # 查找现有的 FIRING 告警
        existing_alert = db.query(Alert).filter(
            Alert.rule_id == rule.id,
            Alert.server_id == rule.server_id,
            Alert.status == AlertStatus.FIRING
        ).first()
        
        if is_triggered:
            if not existing_alert:
                # 检查持续时间：查看过去N分钟内是否一直超过阈值
                duration_minutes = rule.duration or 1  # 默认1分钟
                if duration_minutes > 1:
                    # 检查过去N分钟的数据
                    is_persistent = await self.check_persistent_condition(
                        server.ip_address, rule.metric_type, rule.operator, 
                        rule.threshold, duration_minutes, rule.metric_label
                    )
                    if not is_persistent:
                        logger.debug(f"Rule {rule.id} triggered but not persistent for {duration_minutes} minutes")
                        return
                
                # 创建新告警
                now = datetime.now(get_timezone())
                alert = Alert(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    server_id=rule.server_id,
                    metric_type=rule.metric_type,
                    metric_label=rule.metric_label,
                    current_value=current_value,
                    threshold=rule.threshold,
                    operator=rule.operator,
                    severity=rule.severity,
                    status=AlertStatus.FIRING,
                    fired_at=now,
                    last_occurred_at=now
                )
                db.add(alert)
                db.flush()  # 获取alert.id
                
                logger.info(
                    f"Alert fired: rule={rule.name}, metric={rule.metric_type}, value={current_value:.2f}"
                )
                
                # 发送通知（屏蔽期间跳过）
                if not is_silenced:
                    try:
                        await notification_service.send_alert_notification(db, alert, rule)
                        alert.last_notified_at = now
                    except Exception as e:
                        logger.error(f"Failed to send notification for alert {alert.id}: {e}")
                else:
                    logger.info(f"Alert {alert.id} created but notification suppressed (silenced)")
            else:
                # 更新现有告警的当前值和最后发生时间
                existing_alert.current_value = current_value
                existing_alert.last_occurred_at = datetime.now(get_timezone())
                
                # 检查是否需要重复通知（屏蔽期间跳过）
                if not is_silenced:
                    repeat_interval_minutes = rule.repeat_interval or 30  # 默认30分钟
                    if existing_alert.last_notified_at:
                        from datetime import timezone
                        now = datetime.now(timezone.utc)
                        last_notified = existing_alert.last_notified_at
                        if last_notified.tzinfo is None:
                            last_notified = last_notified.replace(tzinfo=timezone.utc)
                        time_since_last_notification = now - last_notified
                        if time_since_last_notification > timedelta(minutes=repeat_interval_minutes):
                            logger.info(f"Sending repeat notification for alert {existing_alert.id} (interval: {repeat_interval_minutes} minutes)")
                            try:
                                await notification_service.send_alert_notification(db, existing_alert, rule)
                                existing_alert.last_notified_at = now
                            except Exception as e:
                                logger.error(f"Failed to send repeat notification: {e}")
        else:
            if existing_alert:
                # 自动恢复告警
                existing_alert.status = AlertStatus.RESOLVED
                existing_alert.resolved_at = datetime.now(get_timezone())
                logger.info(f"Alert auto-resolved: alert_id={existing_alert.id}, rule={rule.name}, metric={rule.metric_type}")
    
    async def check_persistent_condition(
        self, instance: str, metric_type: str, operator: str, 
        threshold: float, duration_minutes: int, metric_label: str = None
    ) -> bool:
        """
        检查条件是否持续满足
        
        Args:
            instance: 服务器IP
            metric_type: 指标类型
            operator: 操作符
            threshold: 阈值
            duration_minutes: 持续时间（分钟）
            metric_label: 指标标签（挂载点或TCP类型）
        
        Returns:
            是否持续满足条件
        """
        try:
            if ':' not in instance:
                instance = f"{instance}:9100"
            
            # 获取过去N分钟的数据
            duration_str = f"{duration_minutes}m"
            if metric_type == "cpu":
                result = await prometheus_service.get_cpu_usage(instance, duration_str)
            elif metric_type == "memory":
                result = await prometheus_service.get_memory_usage(instance, duration_str)
            elif metric_type == "disk_mount":
                if not metric_label:
                    logger.warning("metric_label is required for disk_mount metric type")
                    return False
                result = await prometheus_service.get_disk_mount_usage(instance, metric_label, duration_str)
            elif metric_type == "tcp_conn":
                if not metric_label:
                    logger.warning("metric_label is required for tcp_conn metric type")
                    return False
                result = await prometheus_service.get_tcp_connections(instance, metric_label, duration_str)
            elif metric_type == "host_up":
                result = await prometheus_service.get_host_up(instance, duration_str)
            else:
                return False
            
            if not result or not result.get("data"):
                if metric_type == "host_up":
                    return self.evaluate_condition(0, operator, threshold)
                return False

            data = result["data"]
            if len(data) < 2:
                if metric_type == "host_up":
                    return all(
                        self.evaluate_condition(point["value"], operator, threshold)
                        for point in data
                    )
                return False
            
            # 检查所有数据点是否都满足条件
            for point in data:
                value = point["value"]
                if not self.evaluate_condition(value, operator, threshold):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking persistent condition: {e}")
            return False
    
    async def get_metric_value(self, instance: str, metric_type: str, metric_label: str = None) -> float:
        """获取监控指标的当前值
        
        Args:
            instance: 实例标识 (IP 或 IP:port)
            metric_type: 指标类型 (cpu, memory, disk_mount, tcp_conn)
            metric_label: 指标标签 (挂载点或 TCP 状态)
        
        Returns:
            指标值
        """
        try:
            # 构建instance标识（IP:端口格式）
            if ':' not in instance:
                instance = f"{instance}:9100"
            
            if metric_type == "cpu":
                result = await prometheus_service.get_cpu_usage(instance, "5m")
            elif metric_type == "memory":
                result = await prometheus_service.get_memory_usage(instance, "5m")
            elif metric_type == "disk_mount":
                # 磁盘挂载点监控
                if not metric_label:
                    logger.warning("metric_label is required for disk_mount metric type")
                    return None
                result = await prometheus_service.get_disk_mount_usage(instance, metric_label, "5m")
            elif metric_type == "tcp_conn":
                if not metric_label:
                    logger.warning("metric_label is required for tcp_conn metric type")
                    return None
                result = await prometheus_service.get_tcp_connections(instance, metric_label, "5m")
            elif metric_type == "host_up":
                return await prometheus_service.get_host_up_value(instance)
            else:
                return None

            if result and result.get("data"):
                data = result["data"]
                if data:
                    return data[-1]["value"]

            if metric_type == "host_up":
                return 0.0

            return None
        except Exception as e:
            logger.error(f"Error getting metric {metric_type} for {instance}: {e}")
            return None
    
    def evaluate_condition(self, current_value: float, operator: str, threshold: float) -> bool:
        """评估告警条件"""
        if operator == ">":
            return current_value > threshold
        elif operator == ">=":
            return current_value >= threshold
        elif operator == "<":
            return current_value < threshold
        elif operator == "<=":
            return current_value <= threshold
        elif operator == "==":
            return abs(current_value - threshold) < 0.01
        else:
            return False
    
    def is_silenced(self, db: Session, rule_id: int, server_id: int) -> bool:
        """检查告警是否被屏蔽"""
        now = datetime.now(get_timezone())
        
        # 检查规则级别的屏蔽
        silence = db.query(AlertSilence).filter(
            AlertSilence.rule_id == rule_id,
            AlertSilence.is_active == True,
            AlertSilence.expires_at > now
        ).first()
        
        if silence:
            return True
        
        # 检查服务器级别的屏蔽
        silence = db.query(AlertSilence).filter(
            AlertSilence.server_id == server_id,
            AlertSilence.rule_id == None,
            AlertSilence.is_active == True,
            AlertSilence.expires_at > now
        ).first()
        
        return silence is not None


# 创建全局实例
alert_checker_service = AlertCheckerService()
