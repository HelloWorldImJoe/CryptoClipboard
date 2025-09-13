"""
加密解密核心模块
提供AES加密和解密功能
"""
import base64
import hashlib
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoManager:
    def __init__(self):
        self.key = None
        self.cipher_suite = None
        
    def set_password(self, password: str, salt: bytes = None) -> bytes:
        """
        设置密码并生成加密密钥
        Args:
            password: 用户密码
            salt: 盐值，如果为None则生成新的
        Returns:
            使用的盐值
        """
        if salt is None:
            salt = os.urandom(16)
        
        # 使用PBKDF2生成密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.key = key
        self.cipher_suite = Fernet(key)
        return salt
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密文本
        Args:
            plaintext: 要加密的明文
        Returns:
            加密后的文本（base64编码）
        """
        if not self.cipher_suite:
            raise ValueError("请先设置密码")
        
        encrypted_data = self.cipher_suite.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密文本
        Args:
            ciphertext: 要解密的密文（base64编码）
        Returns:
            解密后的明文
        """
        if not self.cipher_suite:
            raise ValueError("请先设置密码")
        
        try:
            encrypted_data = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")
    
    def is_encrypted_text(self, text: str) -> bool:
        """
        检查文本是否为加密文本
        通过尝试解密来判断
        """
        if not self.cipher_suite:
            return False
        
        try:
            # 检查是否为有效的base64编码
            base64.urlsafe_b64decode(text.encode())
            # 尝试解密
            self.decrypt(text)
            return True
        except:
            return False
    
    def generate_key_hash(self, password: str, salt: bytes) -> str:
        """
        生成密钥哈希用于验证密码
        """
        return hashlib.sha256((password + salt.hex()).encode()).hexdigest()


# 测试代码
if __name__ == "__main__":
    crypto = CryptoManager()
    
    # 测试加密解密
    password = "test_password"
    salt = crypto.set_password(password)
    
    test_text = "这是一个测试文本，包含中文和English"
    print(f"原文: {test_text}")
    
    # 加密
    encrypted = crypto.encrypt(test_text)
    print(f"加密后: {encrypted}")
    
    # 解密
    decrypted = crypto.decrypt(encrypted)
    print(f"解密后: {decrypted}")
    
    # 验证
    print(f"加密解密成功: {test_text == decrypted}")
    
    # 测试加密文本检测
    print(f"是否为加密文本: {crypto.is_encrypted_text(encrypted)}")
    print(f"普通文本检测: {crypto.is_encrypted_text('普通文本')}")