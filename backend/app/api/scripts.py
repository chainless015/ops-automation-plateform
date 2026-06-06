"""
脚本管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.models.script import Script
from app.schemas.script import ScriptCreate, ScriptUpdate, ScriptResponse, ScriptListItem, ScriptListResponse
from app.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=ScriptListResponse)
def get_scripts(
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取脚本列表
    
    Args:
        search: 搜索关键词（名称或描述）
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        脚本列表（带分页信息）
    """
    query = db.query(Script)
    
    # 搜索
    if search:
        query = query.filter(
            (Script.name.ilike(f"%{search}%")) | 
            (Script.description.ilike(f"%{search}%"))
        )
    
    # 获取总数
    total = query.count()
    
    # 分页
    scripts = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return ScriptListResponse(
        items=[ScriptListItem(**script.to_dict(include_content=False)) for script in scripts],
        total=total
    )


@router.post("", response_model=ScriptResponse, status_code=status.HTTP_201_CREATED)
def create_script(
    script_data: ScriptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建脚本
    
    Args:
        script_data: 脚本数据
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        创建的脚本
    """
    # 创建脚本
    script = Script(
        name=script_data.name,
        description=script_data.description,
        content=script_data.content
    )
    
    db.add(script)
    db.commit()
    db.refresh(script)
    
    logger.info(f"User {current_user.username} created script: {script.name}")
    
    return ScriptResponse(**script.to_dict())


@router.get("/{script_id}", response_model=ScriptResponse)
def get_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取脚本详情
    
    Args:
        script_id: 脚本ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        脚本详情
    
    Raises:
        HTTPException: 脚本不存在时抛出404错误
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    return ScriptResponse(**script.to_dict())


@router.put("/{script_id}", response_model=ScriptResponse)
def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新脚本
    
    Args:
        script_id: 脚本ID
        script_data: 更新数据
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        更新后的脚本
    
    Raises:
        HTTPException: 脚本不存在时抛出404错误
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    # 更新字段
    update_data = script_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(script, field, value)
    
    db.commit()
    db.refresh(script)
    
    logger.info(f"User {current_user.username} updated script: {script.name}")
    
    return ScriptResponse(**script.to_dict())


@router.delete("/{script_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除脚本
    
    Args:
        script_id: 脚本ID
        db: 数据库会话
        current_user: 当前用户
    
    Raises:
        HTTPException: 脚本不存在时抛出404错误
    """
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Script not found"
        )
    
    db.delete(script)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted script: {script.name}")
    
    return None
