"""
数据清理服务
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.execution import ExecutionHistory
from app.core.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


def cleanup_old_executions(days: int = 90):
    """
    清理旧的执行历史记录
    
    Args:
        days: 保留天数，默认90天
    """
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 查询需要删除的记录数
        count = db.query(ExecutionHistory).filter(
            ExecutionHistory.executed_at < cutoff_date
        ).count()
        
        if count > 0:
            # 删除旧记录
            db.query(ExecutionHistory).filter(
                ExecutionHistory.executed_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"Cleaned up {count} execution history records older than {days} days")
        else:
            logger.info(f"No execution history records to clean up (older than {days} days)")
            
    except Exception as e:
        logger.error(f"Error cleaning up execution history: {str(e)}")
        db.rollback()
    finally:
        db.close()
