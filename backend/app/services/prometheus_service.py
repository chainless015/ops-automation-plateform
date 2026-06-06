"""
Prometheus监控服务
"""
import httpx
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class PrometheusService:
    """Prometheus服务类"""
    
    def __init__(self):
        self.base_url = settings.PROMETHEUS_URL
        self.timeout = 30.0
    
    async def query(self, query: str) -> Optional[Dict]:
        """
        执行Prometheus查询
        
        Args:
            query: PromQL查询语句
        
        Returns:
            查询结果
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query",
                    params={"query": query}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Prometheus query error: {e}")
            return None
    
    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "15s"
    ) -> Optional[Dict]:
        """
        执行Prometheus范围查询
        
        Args:
            query: PromQL查询语句
            start: 开始时间
            end: 结束时间
            step: 步长
        
        Returns:
            查询结果
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/query_range",
                    params={
                        "query": query,
                        "start": start.timestamp(),
                        "end": end.timestamp(),
                        "step": step
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Prometheus query_range error: {e}")
            return None
    
    async def check_instance_exists(self, instance: str) -> bool:
        """
        检查实例是否存在于Prometheus中（即是否安装了node_exporter）
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
        
        Returns:
            实例是否存在
        """
        try:
            # 查询up指标，检查该instance是否存在
            query = f'up{{job="node-exporter",instance="{instance}"}}'
            result = await self.query(query)
            
            if result and result.get("status") == "success":
                data = result.get("data", {}).get("result", [])
                # 如果有结果且值为1，说明实例在线
                if data and len(data) > 0:
                    value = data[0].get("value", [None, "0"])
                    return len(value) > 1 and value[1] == "1"
            return False
        except Exception as e:
            logger.error(f"Error checking instance existence: {e}")
            return False
    
    async def get_cpu_usage(self, instance: str, duration: str = "1h") -> Optional[Dict]:
        """
        获取CPU使用率
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            duration: 时间范围
        
        Returns:
            CPU使用率数据
        """
        # CPU使用率 = 100 - (idle时间的百分比)
        # 使用1m时间窗口，更快响应CPU变化
        # 使用clamp_min确保结果不为负数
        query = f'clamp_min((1 - avg(rate(node_cpu_seconds_total{{mode="idle",job="node-exporter",instance="{instance}"}}[1m]))) * 100, 0)'
        end = datetime.now()
        start = end - self._parse_duration(duration)
        
        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "cpu")
        return None
    
    async def get_memory_usage(self, instance: str, duration: str = "1h") -> Optional[Dict]:
        """
        获取内存使用率
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            duration: 时间范围
        
        Returns:
            内存使用率数据
        """
        query = f'clamp_min((1 - (node_memory_MemAvailable_bytes{{job="node-exporter",instance="{instance}"}} / node_memory_MemTotal_bytes{{job="node-exporter",instance="{instance}"}})) * 100, 0)'
        end = datetime.now()
        start = end - self._parse_duration(duration)
        
        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "memory")
        return None
    
    async def get_disk_usage(self, instance: str, duration: str = "1h") -> Optional[Dict]:
        """
        获取磁盘使用率
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            duration: 时间范围
        
        Returns:
            磁盘使用率数据
        """
        query = f'clamp_min((1 - (node_filesystem_avail_bytes{{job="node-exporter",instance="{instance}",mountpoint="/",fstype!~"tmpfs|fuse.lxcfs|squashfs|vfat"}} / node_filesystem_size_bytes{{job="node-exporter",instance="{instance}",mountpoint="/",fstype!~"tmpfs|fuse.lxcfs|squashfs|vfat"}})) * 100, 0)'
        end = datetime.now()
        start = end - self._parse_duration(duration)
        
        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "disk")
        return None
    
    async def get_disk_mount_usage(self, instance: str, mountpoint: str, duration: str = "1h") -> Optional[Dict]:
        """
        获取指定挂载点的磁盘使用率
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            mountpoint: 挂载点（如 "/", "/home", "/data"）
            duration: 时间范围
        
        Returns:
            磁盘使用率数据
        """
        query = f'clamp_min((1 - (node_filesystem_avail_bytes{{job="node-exporter",instance="{instance}",mountpoint="{mountpoint}",fstype!~"tmpfs|fuse.lxcfs|squashfs|vfat"}} / node_filesystem_size_bytes{{job="node-exporter",instance="{instance}",mountpoint="{mountpoint}",fstype!~"tmpfs|fuse.lxcfs|squashfs|vfat"}})) * 100, 0)'
        end = datetime.now()
        start = end - self._parse_duration(duration)
        
        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "disk_mount")
        return None
    
    _TCP_CONN_QUERIES = {
        # 已建立连接：/proc/net/snmp Tcp_CurrEstab
        "CurrEstab": 'node_netstat_Tcp_CurrEstab{{job="node-exporter",instance="{instance}"}}',
        # 所有已分配 TCP 连接
        "AllEstab": 'node_sockstat_TCP_alloc{{job="node-exporter",instance="{instance}"}}',
    }

    def _build_tcp_query(self, instance: str, conn_type: str) -> Optional[str]:
        template = self._TCP_CONN_QUERIES.get(conn_type)
        if not template:
            return None
        return template.format(instance=instance)

    async def get_tcp_connections(
        self, instance: str, conn_type: str, duration: str = "1h"
    ) -> Optional[Dict]:
        """
        获取TCP连接数
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            conn_type: 连接类型（CurrEstab 或 AllEstab）
            duration: 时间范围
        
        Returns:
            TCP连接数数据
        """
        query = self._build_tcp_query(instance, conn_type)
        if not query:
            return None

        end = datetime.now()
        start = end - self._parse_duration(duration)

        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "tcp_conn")
        return None

    async def get_host_up(self, instance: str, duration: str = "1h") -> Optional[Dict]:
        """
        获取主机/node_exporter 存活状态（up 指标：1=在线，0=离线）
        """
        query = f'up{{job="node-exporter",instance="{instance}"}}'
        end = datetime.now()
        start = end - self._parse_duration(duration)

        result = await self.query_range(query, start, end, step="1m")
        if result and result.get("status") == "success":
            return self._format_metrics(result, "host_up")
        return None

    async def get_host_up_value(self, instance: str) -> float:
        """获取当前主机存活状态，无数据时视为离线（0）"""
        query = f'up{{job="node-exporter",instance="{instance}"}}'
        result = await self.query(query)
        if result and result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                try:
                    return float(data[0].get("value", [None, "0"])[1])
                except (ValueError, TypeError, IndexError):
                    pass
        return 0.0

    async def get_all_metrics(self, instance: str, duration: str = "1h") -> Dict:
        """
        获取所有监控指标
        
        Args:
            instance: 实例标识（IP:端口格式，如 "192.168.1.1:9100"）
            duration: 时间范围
        
        Returns:
            所有指标数据
        """
        cpu_data = await self.get_cpu_usage(instance, duration)
        memory_data = await self.get_memory_usage(instance, duration)
        disk_data = await self.get_disk_usage(instance, duration)
        
        return {
            "cpu": cpu_data,
            "memory": memory_data,
            "disk": disk_data
        }
    
    def _parse_duration(self, duration: str) -> timedelta:
        """
        解析时间范围字符串
        
        Args:
            duration: 时间范围（如 "1h", "24h", "7d"）
        
        Returns:
            timedelta对象
        """
        unit = duration[-1]
        value = int(duration[:-1])
        
        if unit == "h":
            return timedelta(hours=value)
        elif unit == "d":
            return timedelta(days=value)
        elif unit == "m":
            return timedelta(minutes=value)
        else:
            return timedelta(hours=1)
    
    def _format_metrics(self, result: Dict, metric_type: str) -> Dict:
        """
        格式化监控指标数据
        
        Args:
            result: Prometheus查询结果
            metric_type: 指标类型
        
        Returns:
            格式化后的数据
        """
        data = []
        statistics = {
            "avg": 0.0,
            "max": 0.0,
            "min": float('inf'),  # 使用float('inf')而不是100.0
            "current": 0.0
        }
        
        if result.get("data", {}).get("result"):
            for series in result["data"]["result"]:
                values = series.get("values", [])
                for timestamp, value in values:
                    try:
                        val = float(value)
                        data.append({
                            "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                            "value": round(val, 2)
                        })
                        
                        # 更新统计值
                        statistics["max"] = max(statistics["max"], val)
                        statistics["min"] = min(statistics["min"], val)
                    except (ValueError, TypeError):
                        continue
            
            # 计算平均值和当前值
            if data:
                statistics["avg"] = round(sum(d["value"] for d in data) / len(data), 2)
                statistics["current"] = data[-1]["value"] if data else 0.0
                statistics["max"] = round(statistics["max"], 2)
                # 如果min仍为inf，设置为0
                if statistics["min"] == float('inf'):
                    statistics["min"] = 0.0
                else:
                    statistics["min"] = round(statistics["min"], 2)
        
        return {
            "metric_type": metric_type,
            "data": data,
            "statistics": statistics
        }


# 创建全局实例
prometheus_service = PrometheusService()
