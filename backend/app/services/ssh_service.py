"""
SSH执行服务
"""
import paramiko
import socket
import time
from typing import Tuple
from app.models.server import Server
from app.core.security import decrypt_ssh_password
import logging

logger = logging.getLogger(__name__)


class SSHConnectionError(Exception):
    """SSH连接异常"""
    pass


class SSHExecutionError(Exception):
    """SSH执行异常"""
    pass


def execute_script_via_ssh(
    server: Server,
    script_content: str,
    timeout: int = 300
) -> Tuple[int, str, str, float]:
    """
    通过SSH在远程服务器执行脚本
    
    Args:
        server: 服务器对象
        script_content: 脚本内容
        timeout: 超时时间（秒）
    
    Returns:
        (return_code, stdout, stderr, duration_seconds)
    
    Raises:
        SSHConnectionError: SSH连接失败
        SSHExecutionError: 脚本执行失败
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    start_time = time.time()
    
    try:
        # 解密SSH密码
        password = decrypt_ssh_password(server.ssh_password)
        
        # 连接服务器
        logger.info(f"Connecting to {server.ip_address}:{server.ssh_port} as {server.ssh_username}")
        ssh.connect(
            hostname=server.ip_address,
            port=server.ssh_port,
            username=server.ssh_username,
            password=password,
            timeout=10
        )
        
        # 使用bash执行脚本内容
        # 将脚本内容通过stdin传递给bash
        command = "bash -s"
        logger.info(f"Executing script on {server.ip_address}")
        stdin, stdout, stderr = ssh.exec_command(
            command,
            timeout=timeout
        )
        
        # 将脚本内容写入stdin
        stdin.write(script_content)
        stdin.close()
        
        # 获取返回码和输出
        logger.info(f"Waiting for command to complete on {server.ip_address}")
        return_code = stdout.channel.recv_exit_status()
        
        logger.info(f"Reading stdout from {server.ip_address}")
        stdout_text = stdout.read().decode('utf-8', errors='replace')
        
        logger.info(f"Reading stderr from {server.ip_address}")
        stderr_text = stderr.read().decode('utf-8', errors='replace')
        
        duration = time.time() - start_time
        
        logger.info(f"Script execution completed on {server.ip_address}, return_code={return_code}, duration={duration:.2f}s")
        logger.debug(f"stdout length: {len(stdout_text)}, stderr length: {len(stderr_text)}")
        
        return return_code, stdout_text, stderr_text, duration
        
    except paramiko.AuthenticationException as e:
        logger.error(f"SSH authentication failed for {server.ip_address}: {str(e)}")
        raise SSHConnectionError(f"SSH authentication failed: {str(e)}")
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error for {server.ip_address}: {str(e)}")
        raise SSHConnectionError(f"SSH connection error: {str(e)}")
    except socket.timeout as e:
        logger.error(f"Script execution timeout on {server.ip_address}: {str(e)}")
        raise SSHExecutionError(f"Script execution timeout: {str(e)}")
    except Exception as e:
        logger.error(f"Script execution failed on {server.ip_address}: {type(e).__name__}: {str(e)}", exc_info=True)
        raise SSHExecutionError(f"Script execution failed: {type(e).__name__}: {str(e)}")
    finally:
        ssh.close()
        logger.info(f"SSH connection closed for {server.ip_address}")
