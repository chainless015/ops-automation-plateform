"""
通知服务：邮件通知
"""
import asyncio
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.models.alert import Alert, AlertRule, AlertRuleNotification, AlertContact, AlertGroup, AlertGroupMember
from app.models.scheduled_task import ScheduledTask, ScheduledTaskNotification
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务类"""

    def _get_smtp_config(self) -> dict:
        """从环境变量加载SMTP配置"""
        return {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USERNAME,
            "password": settings.SMTP_PASSWORD,
            "from": settings.SMTP_FROM,
            "use_tls": settings.SMTP_USE_TLS
        }

    def _validate_smtp_config(self, smtp_config: dict) -> list[str]:
        missing = []
        if not smtp_config['host']:
            missing.append('SMTP_HOST')
        if not smtp_config['from']:
            missing.append('SMTP_FROM')
        return missing

    def _build_message(self, smtp_config: dict, to_email: str, subject: str, content: str) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        return msg

    def _send_with_server(self, server, smtp_config: dict, to_email: str, subject: str, content: str) -> bool:
        try:
            msg = self._build_message(smtp_config, to_email, subject, content)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except OSError as e:
            logger.warning(f"Network error sending email to {to_email}: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.warning(f"SMTP error sending email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}", exc_info=True)
            return False

    def send_emails(self, to_emails: list[str], subject: str, content: str) -> tuple[int, int]:
        """使用同一 SMTP 连接向多个收件人发送相同内容的邮件"""
        recipients = list(dict.fromkeys(email.strip() for email in to_emails if email and email.strip()))
        if not recipients:
            logger.warning("SMTP configuration incomplete (recipient), skipping email")
            return 0, 0

        smtp_config = self._get_smtp_config()
        missing = self._validate_smtp_config(smtp_config)
        if missing:
            logger.warning(
                "SMTP configuration incomplete (%s), skipping email",
                ', '.join(missing)
            )
            return 0, len(recipients)

        port = smtp_config['port']
        success_count = 0

        try:
            if port == 465:
                logger.info(f"Connecting to {smtp_config['host']}:{port} using SSL")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_config['host'], port, timeout=30, context=context) as server:
                    if smtp_config['username'] and smtp_config['password']:
                        server.login(smtp_config['username'], smtp_config['password'])
                    for email in recipients:
                        if self._send_with_server(server, smtp_config, email, subject, content):
                            success_count += 1
            else:
                logger.info(f"Connecting to {smtp_config['host']}:{port} using STARTTLS")
                with smtplib.SMTP(smtp_config['host'], port, timeout=30) as server:
                    server.ehlo()
                    if smtp_config['use_tls']:
                        server.starttls()
                        server.ehlo()
                    if smtp_config['username'] and smtp_config['password']:
                        server.login(smtp_config['username'], smtp_config['password'])
                    for email in recipients:
                        if self._send_with_server(server, smtp_config, email, subject, content):
                            success_count += 1
        except OSError as e:
            logger.warning(f"Network error connecting to SMTP server: {e}")
        except smtplib.SMTPException as e:
            logger.warning(f"SMTP connection error: {e}")
        except Exception as e:
            logger.error(f"Failed to connect or authenticate SMTP server: {e}", exc_info=True)

        return success_count, len(recipients)

    def format_alert_email(self, alert: Alert, rule: AlertRule, server_hostname: str) -> tuple[str, str]:
        """格式化告警邮件，返回 (subject, content)"""
        severity_colors = {
            "level4": "#dc3545",
            "level3": "#ffc107",
            "level2": "#409EFF",
            "level1": "#909399"
        }
        severity_names = {
            "level1": "1级告警",
            "level2": "2级告警",
            "level3": "3级告警",
            "level4": "4级告警"
        }
        metric_names = {
            "cpu": "CPU使用率",
            "memory": "内存使用率",
            "disk_mount": "磁盘使用率",
            "tcp_conn": "TCP连接数",
            "host_up": "主机存活"
        }

        severity_val = alert.severity.value if hasattr(alert.severity, 'value') else alert.severity
        color = severity_colors.get(severity_val, "#6c757d")
        severity_name = severity_names.get(severity_val, severity_val)
        metric_name = metric_names.get(alert.metric_type, alert.metric_type)

        metric_display = metric_name
        if alert.metric_type == "disk_mount" and alert.metric_label:
            metric_display = f"磁盘使用率 ({alert.metric_label})"
        elif alert.metric_type == "tcp_conn" and alert.metric_label:
            tcp_type_map = {"CurrEstab": "已建立连接", "AllEstab": "所有连接"}
            metric_display = f"TCP连接数 - {tcp_type_map.get(alert.metric_label, alert.metric_label)}"

        fired_at_str = alert.fired_at.strftime('%Y-%m-%d %H:%M:%S') if alert.fired_at else "未知"
        last_occurred_at_str = alert.last_occurred_at.strftime('%Y-%m-%d %H:%M:%S') if alert.last_occurred_at else fired_at_str

        if alert.metric_type == "tcp_conn":
            unit = "个"
            threshold_display = f"{rule.operator} {int(rule.threshold)}{unit}"
            current_value_display = f"{int(alert.current_value)}{unit}"
        elif alert.metric_type == "host_up":
            status_map = {0.0: "离线", 1.0: "在线"}
            current_status = status_map.get(alert.current_value, str(int(alert.current_value)))
            threshold_display = f"{rule.operator} {int(rule.threshold)}（0=离线，1=在线）"
            current_value_display = current_status
        else:
            unit = "%"
            threshold_display = f"{rule.operator} {rule.threshold}{unit}"
            current_value_display = f"{alert.current_value:.2f}{unit}"

        subject = f"【{severity_name}】{rule.name} - {server_hostname}"

        content = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
  .header h2 {{ margin: 0; font-size: 20px; }}
  .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; }}
  .info-row {{ margin: 12px 0; display: flex; align-items: flex-start; }}
  .label {{ font-weight: bold; color: #495057; min-width: 100px; }}
  .value {{ color: #212529; flex: 1; }}
  .highlight {{ color: {color}; font-weight: bold; }}
  .divider {{ height: 1px; background-color: #dee2e6; margin: 15px 0; }}
  .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header"><h2>告警通知</h2></div>
    <div class="content">
      <div class="info-row"><span class="label">告警级别：</span><span class="value"><span class="highlight">{severity_name}</span></span></div>
      <div class="divider"></div>
      <div class="info-row"><span class="label">服务器：</span><span class="value">{server_hostname}</span></div>
      <div class="info-row"><span class="label">监控指标：</span><span class="value">{metric_display}</span></div>
      <div class="divider"></div>
      <div class="info-row"><span class="label">告警条件：</span><span class="value">{threshold_display}</span></div>
      <div class="info-row"><span class="label">当前值：</span><span class="value"><span class="highlight">{current_value_display}</span></span></div>
      <div class="divider"></div>
      <div class="info-row"><span class="label">首次触发：</span><span class="value">{fired_at_str}</span></div>
      <div class="info-row"><span class="label">最后发生：</span><span class="value">{last_occurred_at_str}</span></div>
    </div>
    <div class="footer"><p>此邮件由自动化运维平台自动发送，请勿回复。</p></div>
  </div>
</body>
</html>"""

        return subject, content

    def resolve_recipient_emails(
        self,
        db: Session,
        contact_ids: list[int],
        group_ids: list[int]
    ) -> set[str]:
        recipient_emails = set()

        if contact_ids:
            contacts = db.query(AlertContact).filter(AlertContact.id.in_(contact_ids)).all()
            for contact in contacts:
                if contact.email and contact.enabled:
                    recipient_emails.add(contact.email)

        if group_ids:
            members = db.query(AlertGroupMember).filter(
                AlertGroupMember.group_id.in_(group_ids)
            ).all()
            member_contact_ids = [m.contact_id for m in members]
            if member_contact_ids:
                contacts = db.query(AlertContact).filter(
                    AlertContact.id.in_(member_contact_ids)
                ).all()
                for contact in contacts:
                    if contact.email and contact.enabled:
                        recipient_emails.add(contact.email)

        return recipient_emails

    def format_scheduled_task_email(
        self,
        task: ScheduledTask,
        server_hostname: str,
        success: bool,
        return_code: int | None,
        stderr: str | None,
        duration_seconds: float | None,
        finished_at
    ) -> tuple[str, str]:
        finished_at_str = finished_at.strftime('%Y-%m-%d %H:%M:%S') if finished_at else "未知"
        duration_display = f"{duration_seconds:.2f}秒" if duration_seconds is not None else "-"

        if success:
            subject = f"【定时任务成功】{task.name} - {server_hostname}"
            header_color = "#28a745"
            header_title = "定时任务执行成功"
            status_display = "成功"
        else:
            subject = f"【定时任务失败】{task.name} - {server_hostname}"
            header_color = "#dc3545"
            header_title = "定时任务执行失败"
            status_display = "失败"

        stderr_block = ""
        if not success:
            stderr_display = (stderr or "无").strip()
            if len(stderr_display) > 500:
                stderr_display = stderr_display[:500] + "..."
            stderr_block = f"""
      <div class="info-row"><span class="label">错误输出：</span></div>
      <div class="error-box">{stderr_display}</div>"""

        content = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
  .header {{ background-color: {header_color}; color: white; padding: 15px; border-radius: 5px 5px 0 0; }}
  .header h2 {{ margin: 0; font-size: 20px; }}
  .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; border-top: none; }}
  .info-row {{ margin: 12px 0; display: flex; align-items: flex-start; }}
  .label {{ font-weight: bold; color: #495057; min-width: 100px; }}
  .value {{ color: #212529; flex: 1; }}
  .error-box {{ background-color: #fff; border: 1px solid #f5c6cb; border-radius: 4px; padding: 10px; white-space: pre-wrap; word-break: break-word; color: #721c24; }}
  .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6; font-size: 12px; color: #6c757d; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header"><h2>{header_title}</h2></div>
    <div class="content">
      <div class="info-row"><span class="label">服务器：</span><span class="value">{server_hostname}</span></div>
      <div class="info-row"><span class="label">执行状态：</span><span class="value">{status_display}</span></div>
      <div class="info-row"><span class="label">返回码：</span><span class="value">{return_code if return_code is not None else '-'}</span></div>
      <div class="info-row"><span class="label">耗时：</span><span class="value">{duration_display}</span></div>
      <div class="info-row"><span class="label">完成时间：</span><span class="value">{finished_at_str}</span></div>{stderr_block}
    </div>
    <div class="footer"><p>此邮件由自动化运维平台自动发送，请勿回复。</p></div>
  </div>
</body>
</html>"""
        return subject, content

    async def send_alert_notification(self, db: Session, alert: Alert, rule: AlertRule):
        """发送告警通知邮件"""
        try:
            from app.models.server import Server
            server = db.query(Server).filter(Server.id == alert.server_id).first()
            server_hostname = f"{server.hostname} ({server.ip_address})" if server else f"Server-{alert.server_id}"

            subject, content = self.format_alert_email(alert, rule, server_hostname)

            notifications = db.query(AlertRuleNotification).filter(
                AlertRuleNotification.rule_id == rule.id
            ).all()

            contact_ids = [n.contact_id for n in notifications if n.contact_id]
            group_ids = [n.group_id for n in notifications if n.group_id]
            recipient_emails = self.resolve_recipient_emails(db, contact_ids, group_ids)

            if recipient_emails:
                success_count, total = await asyncio.to_thread(
                    self.send_emails,
                    list(recipient_emails),
                    subject,
                    content
                )
                logger.info(
                    "Alert notification for rule %s sent to %s/%s recipients",
                    rule.id,
                    success_count,
                    total
                )
            else:
                logger.warning(f"No recipients configured for alert rule {rule.id}")

        except Exception as e:
            logger.error(f"Failed to send alert notification: {e}", exc_info=True)

    async def send_scheduled_task_notification(
        self,
        db: Session,
        task: ScheduledTask,
        server_hostname: str,
        success: bool,
        return_code: int | None = None,
        stderr: str | None = None,
        duration_seconds: float | None = None,
        finished_at=None
    ):
        """按任务配置发送定时任务执行结果通知"""
        try:
            if success and not task.notify_on_success:
                return
            if not success and not task.notify_on_failure:
                return

            notifications = db.query(ScheduledTaskNotification).filter(
                ScheduledTaskNotification.task_id == task.id
            ).all()
            if not notifications:
                logger.info(f"No notification recipients configured for scheduled task {task.id}")
                return

            contact_ids = [n.contact_id for n in notifications if n.contact_id]
            group_ids = [n.group_id for n in notifications if n.group_id]
            recipient_emails = self.resolve_recipient_emails(db, contact_ids, group_ids)

            if not recipient_emails:
                logger.warning(f"No enabled recipients for scheduled task {task.id}")
                return

            subject, content = self.format_scheduled_task_email(
                task,
                server_hostname,
                success,
                return_code,
                stderr,
                duration_seconds,
                finished_at
            )
            success_count, total = await asyncio.to_thread(
                self.send_emails,
                list(recipient_emails),
                subject,
                content
            )
            result_label = "success" if success else "failure"
            logger.info(
                "Scheduled task %s notification for task %s sent to %s/%s recipients",
                result_label,
                task.id,
                success_count,
                total
            )
        except Exception as e:
            logger.error(f"Failed to send scheduled task notification: {e}", exc_info=True)


# 创建全局实例
notification_service = NotificationService()
