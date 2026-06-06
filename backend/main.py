"""
FastAPI应用主入口
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging_config import setup_logging
import logging
import asyncio
from datetime import datetime, time, timedelta

setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="自动化运维平台API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def disable_api_cache(request: Request, call_next):
    """API 响应禁止缓存，避免前端刷新拿到旧数据"""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


# 全局异常处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理Pydantic验证错误"""
    errors = exc.errors()
    
    # 获取第一个错误
    if errors:
        first_error = errors[0]
        error_type = first_error.get("type", "")
        field = first_error.get("loc", [])[-1] if first_error.get("loc") else "unknown"
        
        # 将验证错误转换为用户友好的消息
        if error_type == "string_too_short":
            detail = f"字段 '{field}' 长度过短"
        elif error_type == "string_too_long":
            detail = f"字段 '{field}' 长度过长"
        elif error_type == "value_error":
            detail = f"字段 '{field}' 值无效"
        else:
            detail = f"字段 '{field}' 验证失败"
    else:
        detail = "请求数据验证失败"
    
    return JSONResponse(
        status_code=422,
        content={"detail": detail}
    )


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} 启动中...")
    logger.info(f"数据库: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    logger.info(f"Prometheus: {settings.PROMETHEUS_URL}")
    
    # 启动时自动同步Prometheus targets
    try:
        from app.core.database import SessionLocal
        from app.api.prometheus_targets import _sync_prometheus_targets_impl
        
        db = SessionLocal()
        _sync_prometheus_targets_impl(db)
        logger.info("Prometheus targets synced on startup")
        db.close()
    except Exception as e:
        logger.warning(f"Failed to sync Prometheus targets on startup: {e}")
    
    # 启动定时清理任务
    asyncio.create_task(scheduled_cleanup_task())
    
    # 启动告警检查服务
    from app.services.alert_checker_service import alert_checker_service
    asyncio.create_task(alert_checker_service.start())
    logger.info("Alert checker service task created")
    
    # 启动定时任务调度服务
    from app.services.scheduler_service import scheduler_service
    scheduler_service.start()
    asyncio.create_task(scheduler_service.run())
    logger.info("Scheduler service task created")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"{settings.APP_NAME} 正在关闭...")
    
    # 停止告警检查服务
    from app.services.alert_checker_service import alert_checker_service
    alert_checker_service.stop()
    
    # 停止定时任务调度服务
    from app.services.scheduler_service import scheduler_service
    scheduler_service.stop()


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


async def scheduled_cleanup_task():
    """定时清理任务（每天凌晨3点执行）"""
    from app.services.cleanup_service import cleanup_old_executions

    while True:
        try:
            # 计算到下一个凌晨3点的秒数
            now = datetime.now()
            target_time = datetime.combine(now.date(), time(3, 0))
            if now.time() >= time(3, 0):
                # 如果已经过了今天的3点，则设置为明天的3点
                target_time = datetime.combine(now.date() + timedelta(days=1), time(3, 0))
            
            wait_seconds = (target_time - now).total_seconds()
            logger.info(f"Next cleanup scheduled at {target_time.isoformat()}")
            
            # 等待到指定时间
            await asyncio.sleep(wait_seconds)
            
            # 执行清理
            logger.info("Starting scheduled cleanup tasks")
            
            # 清理执行历史（保留90天）
            cleanup_old_executions(days=90)
            
            logger.info("Scheduled cleanup tasks completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled cleanup task: {str(e)}")
            # 出错后等待1小时再重试
            await asyncio.sleep(3600)


# 导入路由
from app.api import auth_router
from app.api.servers import router as servers_router
from app.api.monitoring import router as monitoring_router
from app.api.alerts import router as alerts_router
from app.api.scripts import router as scripts_router
from app.api.executions import router as executions_router
from app.api.scheduled_tasks import router as scheduled_tasks_router
from app.api.dashboard import router as dashboard_router
from app.api.prometheus_targets import router as prometheus_targets_router

# 注册路由
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])
app.include_router(servers_router, prefix="/api/servers", tags=["服务器管理"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["监控"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["告警管理"])
app.include_router(scripts_router, prefix="/api/scripts", tags=["脚本管理"])
app.include_router(executions_router, prefix="/api/executions", tags=["执行历史"])
app.include_router(scheduled_tasks_router, prefix="/api/scheduled-tasks", tags=["定时任务"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(prometheus_targets_router, prefix="/api/prometheus", tags=["Prometheus管理"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
