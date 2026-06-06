"""
定时任务API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from zoneinfo import ZoneInfo
from croniter import croniter
from app.core.database import get_db
from app.models.user import User
from app.models.scheduled_task import ScheduledTask, ScheduledTaskNotification
from app.models.alert import AlertContact, AlertGroup
from app.models.script import Script
from app.models.server import Server
from app.schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    ScheduledTaskListItem,
    ScheduledTaskListResponse
)
from app.schemas.alert import AlertContactResponse, AlertGroupResponse
from app.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def _load_task_notifications(db: Session, task_id: int) -> tuple[list, list]:
    notifications = db.query(ScheduledTaskNotification).filter(
        ScheduledTaskNotification.task_id == task_id
    ).all()
    contact_ids = [n.contact_id for n in notifications if n.contact_id]
    group_ids = [n.group_id for n in notifications if n.group_id]

    contacts = db.query(AlertContact).filter(AlertContact.id.in_(contact_ids)).all() if contact_ids else []
    groups = db.query(AlertGroup).filter(AlertGroup.id.in_(group_ids)).all() if group_ids else []
    return (
        [AlertContactResponse(**c.to_dict()) for c in contacts],
        [AlertGroupResponse(**g.to_dict()) for g in groups]
    )


def _build_task_response(db: Session, task: ScheduledTask) -> ScheduledTaskResponse:
    task_dict = task.to_dict()
    contacts, groups = _load_task_notifications(db, task.id)
    task_dict["contacts"] = contacts
    task_dict["groups"] = groups
    return ScheduledTaskResponse(**task_dict)


def _build_task_list_item(db: Session, task: ScheduledTask) -> ScheduledTaskListItem:
    task_dict = task.to_dict()
    contacts, groups = _load_task_notifications(db, task.id)
    task_dict["contacts"] = contacts
    task_dict["groups"] = groups
    return ScheduledTaskListItem(**task_dict)


def _sync_task_notifications(
    db: Session,
    task_id: int,
    contact_ids: Optional[List[int]],
    group_ids: Optional[List[int]]
):
    if contact_ids is None and group_ids is None:
        return

    db.query(ScheduledTaskNotification).filter(
        ScheduledTaskNotification.task_id == task_id
    ).delete()

    for contact_id in contact_ids or []:
        db.add(ScheduledTaskNotification(task_id=task_id, contact_id=contact_id))
    for group_id in group_ids or []:
        db.add(ScheduledTaskNotification(task_id=task_id, group_id=group_id))


@router.get("", response_model=ScheduledTaskListResponse)
def get_scheduled_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    enabled: Optional[bool] = Query(None, description="是否启用筛选"),
    script_id: Optional[int] = Query(None, description="脚本ID筛选"),
    server_id: Optional[int] = Query(None, description="服务器ID筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(ScheduledTask)

    if enabled is not None:
        query = query.filter(ScheduledTask.enabled == enabled)
    if script_id:
        query = query.filter(ScheduledTask.script_id == script_id)
    if server_id:
        query = query.filter(ScheduledTask.server_id == server_id)

    total = query.count()
    tasks = query.order_by(ScheduledTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return ScheduledTaskListResponse(
        items=[_build_task_list_item(db, task) for task in tasks],
        total=total
    )


@router.post("", response_model=ScheduledTaskResponse, status_code=status.HTTP_201_CREATED)
def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    script = db.query(Script).filter(Script.id == task_data.script_id).first()
    if not script:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")

    server = db.query(Server).filter(Server.id == task_data.server_id).first()
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    try:
        cron = croniter(task_data.cron_expression, datetime.now(SHANGHAI_TZ))
        next_run = cron.get_next(datetime)
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=SHANGHAI_TZ)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cron expression: {str(e)}"
        )

    task = ScheduledTask(
        name=task_data.name,
        description=task_data.description,
        script_id=task_data.script_id,
        server_id=task_data.server_id,
        cron_expression=task_data.cron_expression,
        enabled=task_data.enabled,
        notify_on_success=task_data.notify_on_success,
        notify_on_failure=task_data.notify_on_failure,
        next_run_at=next_run if task_data.enabled else None
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    _sync_task_notifications(db, task.id, task_data.contact_ids, task_data.group_ids)
    db.commit()

    logger.info(f"User {current_user.username} created scheduled task: {task.name}")
    return _build_task_response(db, task)


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
def get_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    return _build_task_response(db, task)


@router.put("/{task_id}", response_model=ScheduledTaskResponse)
def update_scheduled_task(
    task_id: int,
    task_data: ScheduledTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    if task_data.script_id:
        script = db.query(Script).filter(Script.id == task_data.script_id).first()
        if not script:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")

    if task_data.server_id:
        server = db.query(Server).filter(Server.id == task_data.server_id).first()
        if not server:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    update_data = task_data.model_dump(exclude_unset=True, exclude={"contact_ids", "group_ids"})

    if 'cron_expression' in update_data or 'enabled' in update_data:
        cron_expr = update_data.get('cron_expression', task.cron_expression)
        is_enabled = update_data.get('enabled', task.enabled)

        if is_enabled:
            try:
                cron = croniter(cron_expr, datetime.now(SHANGHAI_TZ))
                next_run = cron.get_next(datetime)
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=SHANGHAI_TZ)
                task.next_run_at = next_run
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid cron expression: {str(e)}"
                )
        else:
            task.next_run_at = None

    for field, value in update_data.items():
        setattr(task, field, value)

    _sync_task_notifications(db, task.id, task_data.contact_ids, task_data.group_ids)

    db.commit()
    db.refresh(task)

    logger.info(f"User {current_user.username} updated scheduled task: {task.name}")
    return _build_task_response(db, task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    db.delete(task)
    db.commit()

    logger.info(f"User {current_user.username} deleted scheduled task: {task.name}")
    return None


@router.post("/{task_id}/toggle", response_model=ScheduledTaskResponse)
def toggle_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(ScheduledTask).filter(ScheduledTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scheduled task not found")

    task.enabled = not task.enabled

    if task.enabled:
        try:
            cron = croniter(task.cron_expression, datetime.now(SHANGHAI_TZ))
            next_run = cron.get_next(datetime)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=SHANGHAI_TZ)
            task.next_run_at = next_run
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cron expression: {str(e)}"
            )
    else:
        task.next_run_at = None

    db.commit()
    db.refresh(task)

    logger.info(f"User {current_user.username} toggled scheduled task {task.name} to {'enabled' if task.enabled else 'disabled'}")
    return _build_task_response(db, task)
