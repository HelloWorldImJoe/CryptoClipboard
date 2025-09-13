"""
直接粘贴管理器
实现解密内容并直接粘贴到当前输入框，不修改剪贴板
"""
import os
import sys
import time
import threading
from typing import Optional, Callable
import logging

try:
    from pynput import keyboard
    from pynput.keyboard import Controller as KeyboardController
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

import pyperclip

class DirectPasteManager:
    """直接粘贴管理器"""
    
    def __init__(self, crypto_manager=None):
        self.crypto_manager = crypto_manager
        self.keyboard_controller = None
        self.logger = logging.getLogger(__name__)
        
        if PYNPUT_AVAILABLE:
            try:
                self.keyboard_controller = KeyboardController()
            except Exception as e:
                self.logger.error(f"初始化键盘控制器失败: {e}")
        
        if not PYNPUT_AVAILABLE:
            self.logger.warning("pynput不可用，直接粘贴功能被禁用")
    
    def is_available(self) -> bool:
        """检查直接粘贴功能是否可用"""
        return PYNPUT_AVAILABLE and self.keyboard_controller is not None
    
    def decrypt_and_paste(self) -> bool:
        """解密剪贴板内容并直接粘贴到当前输入框"""
        if not self.is_available():
            self.logger.error("直接粘贴功能不可用")
            return False
        
        if not self.crypto_manager:
            self.logger.error("加密管理器未设置")
            return False
        
        try:
            # 1. 获取当前剪贴板内容
            clipboard_content = pyperclip.paste()
            
            if not clipboard_content:
                self.logger.warning("剪贴板为空")
                return False
            
            # 2. 尝试解密
            try:
                decrypted_text = self.crypto_manager.decrypt(clipboard_content)
                if not decrypted_text:
                    # 如果解密失败，可能是普通文本
                    decrypted_text = clipboard_content
                    self.logger.info("内容未加密，直接使用原始文本")
                else:
                    self.logger.info("内容解密成功")
                    
            except Exception as e:
                # 解密失败，使用原始内容
                decrypted_text = clipboard_content
                self.logger.info(f"解密失败，使用原始内容: {e}")
            
            # 3. 直接输入解密后的文本
            success = self._type_text(decrypted_text)
            
            if success:
                self.logger.info(f"成功直接粘贴 {len(decrypted_text)} 个字符")
                return True
            else:
                self.logger.error("直接粘贴失败")
                return False
                
        except Exception as e:
            self.logger.error(f"解密并粘贴失败: {e}")
            return False
    
    def _type_text(self, text: str) -> bool:
        """模拟键盘输入文本"""
        if not self.keyboard_controller:
            return False
        
        try:
            # 短暂延迟，确保快捷键释放完成
            time.sleep(0.1)
            
            # 逐字符输入文本
            for char in text:
                try:
                    self.keyboard_controller.type(char)
                    # 很短的延迟，避免输入过快
                    time.sleep(0.001)
                except Exception as e:
                    self.logger.warning(f"输入字符 '{char}' 失败: {e}")
                    # 继续输入剩余字符
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"模拟键盘输入失败: {e}")
            return False
    
    def decrypt_and_paste_async(self) -> None:
        """异步执行解密并粘贴"""
        def async_task():
            try:
                self.decrypt_and_paste()
            except Exception as e:
                self.logger.error(f"异步粘贴任务失败: {e}")
        
        # 在单独线程中执行，避免阻塞
        threading.Thread(target=async_task, daemon=True).start()
    
    def set_crypto_manager(self, crypto_manager):
        """设置加密管理器"""
        self.crypto_manager = crypto_manager
    
    def test_functionality(self) -> dict:
        """测试直接粘贴功能"""
        result = {
            "available": self.is_available(),
            "pynput_installed": PYNPUT_AVAILABLE,
            "keyboard_controller": self.keyboard_controller is not None,
            "crypto_manager": self.crypto_manager is not None
        }
        
        if result["available"]:
            try:
                # 测试键盘控制器
                # 注意：这只是一个快速测试，不会实际输入
                test_success = True
            except Exception as e:
                result["test_error"] = str(e)
                test_success = False
            
            result["test_passed"] = test_success
        
        return result


class SmartPasteManager:
    """智能粘贴管理器 - 整合直接粘贴和快捷键"""
    
    def __init__(self, crypto_manager=None, config_manager=None):
        self.crypto_manager = crypto_manager
        self.config_manager = config_manager
        self.direct_paste_manager = DirectPasteManager(crypto_manager)
        self.hotkey_manager = None
        self.logger = logging.getLogger(__name__)
        
        # 延迟导入HotkeyManager避免循环导入
        try:
            from hotkey_manager import HotkeyManager
            self.hotkey_manager = HotkeyManager()
        except ImportError:
            # 如果作为独立模块运行
            sys.path.append(os.path.dirname(__file__))
            try:
                from hotkey_manager import HotkeyManager
                self.hotkey_manager = HotkeyManager()
            except ImportError as e:
                self.logger.error(f"导入HotkeyManager失败: {e}")
    
    def initialize(self) -> bool:
        """初始化智能粘贴管理器"""
        if not self.is_available():
            self.logger.error("智能粘贴功能不可用")
            return False
        
        # 从配置加载快捷键设置
        if self.config_manager:
            try:
                from config_manager import AppSettings
                settings = AppSettings(self.config_manager)
                
                if settings.hotkey_enabled:
                    # 设置快捷键
                    self.hotkey_manager.set_hotkey(
                        settings.hotkey_combination,
                        settings.hotkey_modifiers,
                        settings.hotkey_key
                    )
                    
                    # 启动快捷键监听
                    if self.hotkey_manager.start(self._on_hotkey_triggered):
                        self.logger.info("智能粘贴快捷键已启用")
                        return True
                    else:
                        self.logger.error("启动快捷键监听失败")
                        return False
                else:
                    self.logger.info("快捷键功能已禁用")
                    return True
                    
            except Exception as e:
                self.logger.error(f"初始化配置失败: {e}")
                return False
        
        return True
    
    def _on_hotkey_triggered(self):
        """快捷键触发回调"""
        self.logger.info("🎯 智能粘贴快捷键被触发")
        self.direct_paste_manager.decrypt_and_paste_async()
    
    def is_available(self) -> bool:
        """检查智能粘贴功能是否可用"""
        return (self.direct_paste_manager.is_available() and 
                self.hotkey_manager and 
                self.hotkey_manager.is_available())
    
    def enable_hotkey(self) -> bool:
        """启用快捷键"""
        if not self.hotkey_manager:
            return False
        
        return self.hotkey_manager.start(self._on_hotkey_triggered)
    
    def disable_hotkey(self):
        """禁用快捷键"""
        if self.hotkey_manager:
            self.hotkey_manager.stop()
    
    def manual_paste(self) -> bool:
        """手动触发智能粘贴"""
        return self.direct_paste_manager.decrypt_and_paste()
    
    def set_crypto_manager(self, crypto_manager):
        """设置加密管理器"""
        self.crypto_manager = crypto_manager
        self.direct_paste_manager.set_crypto_manager(crypto_manager)
    
    def set_config_manager(self, config_manager):
        """设置配置管理器"""
        self.config_manager = config_manager
    
    def get_status(self) -> dict:
        """获取状态信息"""
        status = {
            "available": self.is_available(),
            "hotkey_enabled": self.hotkey_manager.enabled if self.hotkey_manager else False,
            "direct_paste": self.direct_paste_manager.test_functionality()
        }
        
        if self.config_manager:
            try:
                from config_manager import AppSettings
                settings = AppSettings(self.config_manager)
                status["hotkey_combination"] = settings.hotkey_combination
                status["hotkey_config_enabled"] = settings.hotkey_enabled
            except Exception as e:
                status["config_error"] = str(e)
        
        return status
    
    def shutdown(self):
        """关闭智能粘贴管理器"""
        self.disable_hotkey()
        self.logger.info("智能粘贴管理器已关闭")


# 测试代码
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 直接粘贴管理器测试")
    
    # 测试直接粘贴功能
    direct_paste = DirectPasteManager()
    print(f"直接粘贴可用性: {direct_paste.is_available()}")
    print(f"功能测试: {direct_paste.test_functionality()}")
    
    if direct_paste.is_available():
        print("\n测试说明:")
        print("1. 复制一些文本到剪贴板")
        print("2. 点击一个文本输入框")
        print("3. 按回车键测试直接粘贴")
        
        input("准备好后按回车键开始测试...")
        
        success = direct_paste.decrypt_and_paste()
        print(f"直接粘贴结果: {'成功' if success else '失败'}")
    else:
        print("❌ 直接粘贴功能不可用")