"""
定时任务调度服务
"""
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from croniter import croniter
from app.core.database import SessionLocal
from app.models.scheduled_task import ScheduledTask
from app.models.execution import ExecutionHistory
from app.services.ssh_service import execute_script_via_ssh, SSHConnectionError, SSHExecutionError
from app.services.notification_service import notification_service
from app.models.script import Script
from app.models.server import Server

logger = logging.getLogger(__name__)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


class SchedulerService:
    """定时任务调度服务"""

    def __init__(self):
        self.running = False
        self.check_interval = 30

    def start(self):
        self.running = True
        logger.info("Scheduler service started")

    def stop(self):
        self.running = False
        logger.info("Scheduler service stopped")

    async def run(self):
        while self.running:
            try:
                await self._check_and_execute_tasks()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}", exc_info=True)
            await asyncio.sleep(self.check_interval)

    async def _notify_task_result(self, task_id: int, success: bool, execution_id: int | None = None):
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
            if not task:
                return

            if success and not task.notify_on_success:
                return
            if not success and not task.notify_on_failure:
                return

            server = db.query(Server).filter(Server.id == task.server_id).first()
            if server:
                server_hostname = f"{server.hostname} ({server.ip_address})"
            else:
                server_hostname = f"Server-{task.server_id}"

            execution = None
            if execution_id:
                execution = db.query(ExecutionHistory).filter(
                    ExecutionHistory.id == execution_id
                ).first()

            await notification_service.send_scheduled_task_notification(
                db,
                task,
                server_hostname,
                success=success,
                return_code=execution.return_code if execution else None,
                stderr=execution.stderr if execution else None,
                duration_seconds=execution.duration_seconds if execution else None,
                finished_at=execution.finished_at if execution else datetime.now(SHANGHAI_TZ)
            )
        except Exception as e:
            logger.error(f"Failed to notify task result for task {task_id}: {e}", exc_info=True)
        finally:
            db.close()

    async def _check_and_execute_tasks(self):
        db = SessionLocal()
        try:
            now = datetime.now(SHANGHAI_TZ)
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.enabled == True,
                (ScheduledTask.next_run_at <= now) | (ScheduledTask.next_run_at == None)
            ).all()

            for task in tasks:
                try:
                    if task.next_run_at is None:
                        cron = croniter(task.cron_expression, now)
                        next_run = cron.get_next(datetime)
                        if next_run.tzinfo is None:
                            next_run = next_run.replace(tzinfo=SHANGHAI_TZ)
                        task.next_run_at = next_run
                        db.commit()
                        logger.info(f"Task {task.id} ({task.name}) scheduled for {next_run}")
                        continue

                    logger.info(f"Executing scheduled task {task.id} ({task.name})")
                    await self._execute_task(task, db)

                    cron = croniter(task.cron_expression, now)
                    next_run = cron.get_next(datetime)
                    if next_run.tzinfo is None:
                        next_run = next_run.replace(tzinfo=SHANGHAI_TZ)
                    task.next_run_at = next_run
                    task.last_run_at = now
                    db.commit()

                    logger.info(f"Task {task.id} ({task.name}) completed, next run at {next_run}")

                except Exception as e:
                    logger.error(f"Error executing task {task.id}: {str(e)}", exc_info=True)
                    task.last_run_status = "failed"
                    db.commit()
                    await self._notify_task_result(task.id, success=False)

        finally:
            db.close()

    async def _execute_task(self, task: ScheduledTask, db):
        script = db.query(Script).filter(Script.id == task.script_id).first()
        server = db.query(Server).filter(Server.id == task.server_id).first()

        if not script or not server:
            logger.error(f"Script or server not found for task {task.id}")
            task.last_run_status = "failed"
            db.commit()
            await self._notify_task_result(task.id, success=False)
            return

        execution = ExecutionHistory(
            script_id=task.script_id,
            server_id=task.server_id,
            status="running",
            execution_type="scheduled"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        asyncio.create_task(
            self._run_script_async(execution.id, task.script_id, task.server_id, task.id)
        )
        task.last_run_status = "running"

    async def _run_script_async(self, execution_id: int, script_id: int, server_id: int, task_id: int = None):
        db = SessionLocal()
        try:
            script = db.query(Script).filter(Script.id == script_id).first()
            server = db.query(Server).filter(Server.id == server_id).first()

            if not script or not server:
                logger.error(f"Script or server not found for execution {execution_id}")
                execution = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
                if execution:
                    execution.status = "failed"
                    execution.stderr = "Script or server not found"
                    execution.finished_at = datetime.now(SHANGHAI_TZ)
                    db.commit()

                if task_id:
                    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                    if task:
                        task.last_run_status = "failed"
                        db.commit()
                    await self._notify_task_result(task_id, success=False, execution_id=execution_id)
                return

            loop = asyncio.get_event_loop()
            return_code, stdout, stderr, duration = await loop.run_in_executor(
                None,
                execute_script_via_ssh,
                server,
                script.content,
                300
            )

            execution = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
            if execution:
                execution.status = "success" if return_code == 0 else "failed"
                execution.return_code = return_code
                execution.stdout = stdout
                execution.stderr = stderr
                execution.duration_seconds = duration
                execution.finished_at = datetime.now(SHANGHAI_TZ)
                db.commit()

                logger.info(f"Scheduled execution {execution_id} completed: status={execution.status}")

                if task_id:
                    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                    if task:
                        task.last_run_status = execution.status
                        db.commit()
                    await self._notify_task_result(
                        task_id,
                        success=execution.status == "success",
                        execution_id=execution_id
                    )

        except (SSHConnectionError, SSHExecutionError) as e:
            logger.error(f"SSH error for execution {execution_id}: {str(e)}")
            execution = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
            if execution:
                execution.status = "failed"
                execution.stderr = str(e)
                execution.finished_at = datetime.now(SHANGHAI_TZ)
                db.commit()

            if task_id:
                task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if task:
                    task.last_run_status = "failed"
                    db.commit()
                await self._notify_task_result(task_id, success=False, execution_id=execution_id)

        except Exception as e:
            logger.error(f"Unexpected error for execution {execution_id}: {str(e)}", exc_info=True)
            execution = db.query(ExecutionHistory).filter(ExecutionHistory.id == execution_id).first()
            if execution:
                execution.status = "failed"
                execution.stderr = f"Unexpected error: {str(e)}"
                execution.finished_at = datetime.now(SHANGHAI_TZ)
                db.commit()

            if task_id:
                task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
                if task:
                    task.last_run_status = "failed"
                    db.commit()
                await self._notify_task_result(task_id, success=False, execution_id=execution_id)

        finally:
            db.close()


scheduler_service = SchedulerService()
