"""
安全相关功能：密码加密、JWT认证、SSH密码加密
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from .config import settings
import base64

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SSH密码加密（使用Fernet对称加密）
def get_cipher():
    """获取加密器"""
    if settings.ENCRYPTION_KEY:
        # 确保密钥是32字节的base64编码
        key = settings.ENCRYPTION_KEY.encode()
        if len(key) < 32:
            key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        return Fernet(key)
    else:
        # 如果没有配置密钥，生成一个临时密钥（不推荐用于生产环境）
        return Fernet(Fernet.generate_key())


def hash_password(password: str) -> str:
    """
    加密密码
    
    Args:
        password: 明文密码
    
    Returns:
        加密后的密码哈希
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 加密后的密码哈希
    
    Returns:
        密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据（通常包含user_id, username, role）
        expires_delta: 过期时间增量
    
    Returns:
        JWT令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT访问令牌
    
    Args:
        token: JWT令牌字符串
    
    Returns:
        解码后的数据字典，如果令牌无效返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def encrypt_ssh_password(password: str) -> str:
    """
    加密SSH密码
    
    Args:
        password: 明文密码
    
    Returns:
        加密后的密码字符串
    """
    cipher = get_cipher()
    encrypted = cipher.encrypt(password.encode())
    return encrypted.decode()


def decrypt_ssh_password(encrypted_password: str) -> str:
    """
    解密SSH密码
    
    Args:
        encrypted_password: 加密后的密码字符串
    
    Returns:
        明文密码
    """
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_password.encode())
    return decrypted.decode()
