"""
剪贴板管理器
监控剪贴板变化，实现自动加密和解密功能
"""
import threading
import time
import pyperclip
from typing import Callable, Optional

# 尝试相对导入，如果失败则使用绝对导入
try:
    from crypto_manager import CryptoManager
except ImportError:
    from crypto_manager import CryptoManager


class ClipboardManager:
    def __init__(self, crypto_manager: CryptoManager):
        self.crypto_manager = crypto_manager
        self.is_running = False
        self.monitor_thread = None
        self.last_clipboard_content = ""
        self.encryption_enabled = False
        self.auto_decrypt_enabled = True
        
        # 回调函数
        self.on_clipboard_changed: Optional[Callable[[str, str], None]] = None
        self.on_encryption_performed: Optional[Callable[[str], None]] = None
        self.on_decryption_performed: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_encryption_status_changed: Optional[Callable[[str, int], None]] = None
        
        # 防止递归加密 - 改进的防递归机制
        self._processing = False
        self._last_processed_content = ""
        self._ignore_next_change = False
        self._processing_start_time = 0
        
    def start_monitoring(self):
        """开始监控剪贴板"""
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_clipboard, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """停止监控剪贴板"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
    
    def enable_encryption(self, enabled: bool = True):
        """启用/禁用自动加密"""
        self.encryption_enabled = enabled
    
    def enable_auto_decrypt(self, enabled: bool = True):
        """启用/禁用自动解密"""
        self.auto_decrypt_enabled = enabled
    
    def _monitor_clipboard(self):
        """监控剪贴板变化的主循环"""
        self.last_clipboard_content = self._get_clipboard_content()
        
        while self.is_running:
            try:
                current_content = self._get_clipboard_content()
                
                # 改进的防递归检查
                should_process = (
                    current_content != self.last_clipboard_content and 
                    not self._processing and 
                    not self._ignore_next_change and
                    (current_content != self._last_processed_content or 
                     time.time() - self._processing_start_time > 5)  # 5秒后允许重新处理相同内容
                )
                
                if should_process:
                    self._handle_clipboard_change(self.last_clipboard_content, current_content)
                    self.last_clipboard_content = current_content
                elif self._ignore_next_change:
                    # 重置忽略标志
                    self._ignore_next_change = False
                    self.last_clipboard_content = current_content
                
                time.sleep(0.5)  # 每500ms检查一次
                
            except Exception as e:
                if self.on_error:
                    self.on_error(f"剪贴板监控错误: {str(e)}")
                time.sleep(1)  # 出错时延长检查间隔
    
    def _get_clipboard_content(self) -> str:
        """获取剪贴板内容"""
        try:
            content = pyperclip.paste()
            return content if content else ""
        except Exception:
            return ""
    
    def _set_clipboard_content(self, content: str):
        """设置剪贴板内容"""
        try:
            self._processing = True
            self._last_processed_content = content
            self._processing_start_time = time.time()
            self._ignore_next_change = True  # 忽略下一次变化（因为是我们自己设置的）
            
            pyperclip.copy(content)
            time.sleep(0.2)  # 给剪贴板更多时间更新
            
            self._processing = False
        except Exception as e:
            self._processing = False
            self._ignore_next_change = False
            if self.on_error:
                self.on_error(f"设置剪贴板失败: {str(e)}")
    
    def _handle_clipboard_change(self, old_content: str, new_content: str):
        """处理剪贴板变化"""
        try:
            # 通知剪贴板变化
            if self.on_clipboard_changed:
                self.on_clipboard_changed(old_content, new_content)
            
            # 如果新内容为空，不处理
            if not new_content.strip():
                return
            
            # 检查是否为加密文本
            is_encrypted = self.crypto_manager.is_encrypted_text(new_content)
            
            # 新的逻辑：剪贴板始终保持加密状态
            if not is_encrypted and self.encryption_enabled:
                # 只有普通文本才加密，加密文本保持原样
                self._auto_encrypt(new_content)
            elif is_encrypted:
                # 加密文本保持加密状态，不自动解密
                # 只在需要时提供通知
                if self.on_encryption_status_changed:
                    self.on_encryption_status_changed("encrypted", len(new_content))
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"处理剪贴板变化失败: {str(e)}")
    
    def _auto_encrypt(self, plaintext: str):
        """自动加密文本"""
        try:
            encrypted_text = self.crypto_manager.encrypt(plaintext)
            self._set_clipboard_content(encrypted_text)
            
            if self.on_encryption_performed:
                self.on_encryption_performed(plaintext)
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"自动加密失败: {str(e)}")
    
    def _auto_decrypt(self, ciphertext: str):
        """自动解密文本"""
        try:
            decrypted_text = self.crypto_manager.decrypt(ciphertext)
            self._set_clipboard_content(decrypted_text)
            
            if self.on_decryption_performed:
                self.on_decryption_performed(decrypted_text)
                
        except Exception as e:
            if self.on_error:
                self.on_error(f"自动解密失败: {str(e)}")
    
    def manual_encrypt(self) -> bool:
        """手动加密当前剪贴板内容"""
        try:
            content = self._get_clipboard_content()
            if not content.strip():
                if self.on_error:
                    self.on_error("剪贴板为空")
                return False
            
            if self.crypto_manager.is_encrypted_text(content):
                if self.on_error:
                    self.on_error("内容已经是加密文本")
                return False
            
            encrypted_text = self.crypto_manager.encrypt(content)
            self._set_clipboard_content(encrypted_text)
            
            if self.on_encryption_performed:
                self.on_encryption_performed(content)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"手动加密失败: {str(e)}")
            return False
    
    def manual_decrypt(self) -> bool:
        """手动解密当前剪贴板内容"""
        try:
            content = self._get_clipboard_content()
            if not content.strip():
                if self.on_error:
                    self.on_error("剪贴板为空")
                return False
            
            if not self.crypto_manager.is_encrypted_text(content):
                if self.on_error:
                    self.on_error("内容不是加密文本")
                return False
            
            decrypted_text = self.crypto_manager.decrypt(content)
            self._set_clipboard_content(decrypted_text)
            
            if self.on_decryption_performed:
                self.on_decryption_performed(decrypted_text)
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"手动解密失败: {str(e)}")
            return False
    
    def temporary_decrypt(self, duration_seconds: int = 10) -> bool:
        """临时解密剪贴板内容，指定时间后自动重新加密"""
        try:
            content = self._get_clipboard_content()
            if not content.strip():
                if self.on_error:
                    self.on_error("剪贴板为空")
                return False
            
            if not self.crypto_manager.is_encrypted_text(content):
                if self.on_error:
                    self.on_error("内容不是加密文本")
                return False
            
            # 保存原始加密内容
            original_encrypted = content
            
            # 解密
            decrypted_text = self.crypto_manager.decrypt(content)
            self._set_clipboard_content(decrypted_text)
            
            if self.on_decryption_performed:
                self.on_decryption_performed(f"{decrypted_text} (临时解密 {duration_seconds}秒)")
            
            # 启动定时器重新加密
            def re_encrypt():
                time.sleep(duration_seconds)
                try:
                    current = self._get_clipboard_content()
                    # 只有当剪贴板内容没有被用户更改时才重新加密
                    if current == decrypted_text:
                        self._set_clipboard_content(original_encrypted)
                        if self.on_encryption_performed:
                            self.on_encryption_performed(f"自动重新加密: {decrypted_text[:20]}...")
                except Exception as e:
                    if self.on_error:
                        self.on_error(f"自动重新加密失败: {str(e)}")
            
            # 在后台线程中执行重新加密
            re_encrypt_thread = threading.Thread(target=re_encrypt, daemon=True)
            re_encrypt_thread.start()
            
            return True
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"临时解密失败: {str(e)}")
            return False
    
    def peek_decrypt(self) -> str:
        """预览解密内容，不修改剪贴板"""
        try:
            content = self._get_clipboard_content()
            if not content.strip():
                return ""
            
            if not self.crypto_manager.is_encrypted_text(content):
                return content  # 如果不是加密文本，直接返回
            
            # 解密但不设置到剪贴板
            decrypted_text = self.crypto_manager.decrypt(content)
            return decrypted_text
            
        except Exception as e:
            if self.on_error:
                self.on_error(f"预览解密失败: {str(e)}")
            return ""
    
    def get_current_clipboard_info(self) -> dict:
        """获取当前剪贴板信息"""
        content = self._get_clipboard_content()
        is_encrypted = self.crypto_manager.is_encrypted_text(content) if content else False
        
        return {
            'content': content,
            'is_encrypted': is_encrypted,
            'length': len(content),
            'has_content': bool(content.strip())
        }


# 测试代码
if __name__ == "__main__":
    from crypto_manager import CryptoManager
    
    # 创建加密管理器
    crypto = CryptoManager()
    crypto.set_password("test_password")
    
    # 创建剪贴板管理器
    clipboard_manager = ClipboardManager(crypto)
    
    # 设置回调函数
    def on_clipboard_changed(old, new):
        print(f"剪贴板变化: {old[:20]}... -> {new[:20]}...")
    
    def on_encryption(original):
        print(f"已加密: {original[:20]}...")
    
    def on_decryption(decrypted):
        print(f"已解密: {decrypted[:20]}...")
    
    def on_error(error):
        print(f"错误: {error}")
    
    clipboard_manager.on_clipboard_changed = on_clipboard_changed
    clipboard_manager.on_encryption_performed = on_encryption
    clipboard_manager.on_decryption_performed = on_decryption
    clipboard_manager.on_error = on_error
    
    # 启用自动加密
    clipboard_manager.enable_encryption(True)
    
    # 开始监控
    print("开始监控剪贴板，请复制一些文本...")
    clipboard_manager.start_monitoring()
    
    try:
        # 保持运行
        while True:
            command = input("输入命令 (encrypt/decrypt/info/quit): ").strip().lower()
            
            if command == "quit":
                break
            elif command == "encrypt":
                clipboard_manager.manual_encrypt()
            elif command == "decrypt":
                clipboard_manager.manual_decrypt()
            elif command == "info":
                info = clipboard_manager.get_current_clipboard_info()
                print(f"剪贴板信息: {info}")
    
    except KeyboardInterrupt:
        print("\n正在退出...")
    
    finally:
        clipboard_manager.stop_monitoring()
        print("已停止监控")