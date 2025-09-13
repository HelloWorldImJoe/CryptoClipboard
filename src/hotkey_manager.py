"""
全局快捷键管理器
负责注册、监听和处理全局快捷键
"""
import os
import sys
import threading
import time
from typing import Callable, Optional, Dict, Any
import logging

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode, Listener
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("❌ pynput 库未安装，快捷键功能不可用")
    print("请运行: pip install pynput")

# 导入权限管理器
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from permission_manager import PermissionManager
    PERMISSION_MANAGER_AVAILABLE = True
except ImportError:
    PERMISSION_MANAGER_AVAILABLE = False

class HotkeyManager:
    """全局快捷键管理器"""
    
    def __init__(self):
        self.enabled = False
        self.listener: Optional[Listener] = None
        self.callback: Optional[Callable] = None
        self.hotkey_combination = "ctrl+shift+v"
        self.modifier_keys = {"ctrl", "shift"}
        self.main_key = "v"
        self.pressed_keys = set()
        self.logger = logging.getLogger(__name__)
        
        # 初始化权限管理器
        self.permission_manager = None
        if PERMISSION_MANAGER_AVAILABLE:
            try:
                self.permission_manager = PermissionManager()
            except Exception as e:
                self.logger.warning(f"权限管理器初始化失败: {e}")
        
        if not PYNPUT_AVAILABLE:
            self.logger.warning("pynput不可用，快捷键功能被禁用")
    
    def check_permissions(self) -> bool:
        """检查快捷键所需权限"""
        if not self.permission_manager:
            return True  # 如果没有权限管理器，默认允许
            
        permissions = self.permission_manager.check_all_permissions()
        return permissions["can_use_hotkeys"]
    
    def request_permissions(self) -> bool:
        """请求必要权限"""
        if not self.permission_manager:
            return True
            
        return self.permission_manager.request_all_permissions()
    
    def get_permission_status(self) -> Dict[str, Any]:
        """获取权限状态"""
        if not self.permission_manager:
            return {"available": False, "message": "权限管理器不可用"}
            
        return self.permission_manager.check_all_permissions()
    
    def set_hotkey(self, combination: str, modifiers: list, key: str):
        """设置快捷键组合"""
        self.hotkey_combination = combination.lower()
        self.modifier_keys = set(mod.lower() for mod in modifiers)
        self.main_key = key.lower()
        
        self.logger.info(f"设置快捷键: {combination}")
        
        # 如果当前正在监听，重新启动监听器
        if self.enabled:
            self.stop()
            self.start(self.callback)
    
    def start(self, callback: Callable):
        """启动快捷键监听"""
        if not PYNPUT_AVAILABLE:
            self.logger.error("pynput不可用，无法启动快捷键监听")
            return False
        
        # 检查权限
        if not self.check_permissions():
            self.logger.warning("权限不足，无法启动快捷键监听")
            
            # 尝试请求权限
            if self.permission_manager:
                self.logger.info("尝试请求必要权限...")
                if not self.request_permissions():
                    self.logger.error("权限请求失败，快捷键功能不可用")
                    return False
            else:
                return False
        
        if self.enabled:
            self.logger.warning("快捷键监听已经启动")
            return True
        
        self.callback = callback
        
        try:
            # 创建键盘监听器
            self.listener = Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            
            # 在单独线程中启动监听
            self.listener.start()
            self.enabled = True
            
            self.logger.info(f"快捷键监听已启动: {self.hotkey_combination}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动快捷键监听失败: {e}")
            return False
    
    def stop(self):
        """停止快捷键监听"""
        if not self.enabled:
            return
        
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            self.enabled = False
            self.pressed_keys.clear()
            
            self.logger.info("快捷键监听已停止")
            
        except Exception as e:
            self.logger.error(f"停止快捷键监听失败: {e}")
    
    def _on_key_press(self, key):
        """按键按下事件处理"""
        try:
            key_name = self._get_key_name(key)
            if key_name:
                self.pressed_keys.add(key_name)
                
                # 检查是否匹配快捷键组合
                if self._is_hotkey_pressed():
                    self._trigger_callback()
                    
        except Exception as e:
            self.logger.error(f"处理按键按下事件失败: {e}")
    
    def _on_key_release(self, key):
        """按键释放事件处理"""
        try:
            key_name = self._get_key_name(key)
            if key_name:
                self.pressed_keys.discard(key_name)
                
        except Exception as e:
            self.logger.error(f"处理按键释放事件失败: {e}")
    
    def _get_key_name(self, key) -> Optional[str]:
        """获取按键名称"""
        try:
            if hasattr(key, 'char') and key.char:
                return key.char.lower()
            elif hasattr(key, 'name'):
                # 处理特殊键
                key_name = key.name.lower()
                
                # 标准化修饰键名称
                key_mapping = {
                    'ctrl_l': 'ctrl',
                    'ctrl_r': 'ctrl', 
                    'alt_l': 'alt',
                    'alt_r': 'alt',
                    'alt_gr': 'alt',
                    'shift_l': 'shift',
                    'shift_r': 'shift',
                    'cmd': 'cmd',
                    'cmd_l': 'cmd',
                    'cmd_r': 'cmd',
                    'super_l': 'cmd',
                    'super_r': 'cmd'
                }
                
                return key_mapping.get(key_name, key_name)
            
        except Exception as e:
            self.logger.debug(f"获取按键名称失败: {e}")
            
        return None
    
    def _is_hotkey_pressed(self) -> bool:
        """检查是否按下了完整的快捷键组合"""
        # 检查所有修饰键是否都被按下
        for modifier in self.modifier_keys:
            if modifier not in self.pressed_keys:
                return False
        
        # 检查主键是否被按下
        if self.main_key not in self.pressed_keys:
            return False
        
        # 确保没有额外的修饰键被按下（避免误触发）
        expected_keys = self.modifier_keys | {self.main_key}
        actual_modifiers = self.pressed_keys & {'ctrl', 'alt', 'shift', 'cmd', 'meta', 'super'}
        
        # 允许一些系统键同时按下
        return actual_modifiers <= self.modifier_keys
    
    def _trigger_callback(self):
        """触发回调函数"""
        if self.callback:
            try:
                # 在单独线程中执行回调，避免阻塞键盘监听
                threading.Thread(
                    target=self.callback,
                    daemon=True
                ).start()
                
                self.logger.info("快捷键触发成功")
                
            except Exception as e:
                self.logger.error(f"执行快捷键回调失败: {e}")
    
    def is_available(self) -> bool:
        """检查快捷键功能是否可用"""
        return PYNPUT_AVAILABLE
    
    def get_permission_info(self) -> Dict[str, Any]:
        """获取权限信息（主要针对macOS）"""
        info = {
            "available": PYNPUT_AVAILABLE,
            "platform": os.name,
            "requires_permission": False,
            "permission_message": ""
        }
        
        if os.name != 'nt':  # macOS/Linux
            info["requires_permission"] = True
            info["permission_message"] = (
                "在macOS上，需要授予应用辅助功能权限：\n"
                "1. 打开系统偏好设置\n"
                "2. 选择安全性与隐私\n"
                "3. 点击隐私标签\n"
                "4. 选择辅助功能\n"
                "5. 添加并勾选此应用"
            )
        
        return info
    
    def test_permissions(self) -> bool:
        """测试权限是否正确设置"""
        if not PYNPUT_AVAILABLE:
            return False
        
        try:
            # 尝试创建一个临时监听器来测试权限
            test_listener = Listener(on_press=lambda key: None)
            test_listener.start()
            time.sleep(0.1)  # 短暂等待
            test_listener.stop()
            return True
            
        except Exception as e:
            self.logger.error(f"权限测试失败: {e}")
            return False


# 实用工具函数
def parse_hotkey_combination(combination: str) -> tuple:
    """解析快捷键组合字符串"""
    parts = combination.lower().split('+')
    if len(parts) < 2:
        raise ValueError("快捷键组合至少需要一个修饰键和一个主键")
    
    modifiers = parts[:-1]
    key = parts[-1]
    
    return modifiers, key


def get_default_hotkey() -> str:
    """获取适合当前平台的默认快捷键"""
    if os.name == 'nt':  # Windows
        return "ctrl+shift+v"
    else:  # macOS/Linux
        return "cmd+shift+v"


def validate_hotkey_combination(combination: str) -> bool:
    """验证快捷键组合是否有效"""
    try:
        modifiers, key = parse_hotkey_combination(combination)
        
        valid_modifiers = {'ctrl', 'alt', 'shift', 'cmd', 'meta', 'super'}
        valid_keys = {
            # 字母
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            # 数字
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            # 功能键
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12'
        }
        
        # 检查修饰键
        for modifier in modifiers:
            if modifier not in valid_modifiers:
                return False
        
        # 检查主键
        if key not in valid_keys:
            return False
        
        # 至少需要一个修饰键
        if not modifiers:
            return False
        
        return True
        
    except Exception:
        return False


# 测试代码
if __name__ == "__main__":
    def test_callback():
        print("🎯 快捷键被触发！")
    
    # 创建快捷键管理器
    manager = HotkeyManager()
    
    print("🔧 快捷键管理器测试")
    print(f"可用性: {manager.is_available()}")
    
    if manager.is_available():
        print(f"权限信息: {manager.get_permission_info()}")
        print(f"权限测试: {manager.test_permissions()}")
        
        # 测试快捷键设置
        print("\n测试快捷键: Ctrl+Shift+V")
        manager.set_hotkey("ctrl+shift+v", ["ctrl", "shift"], "v")
        
        if manager.start(test_callback):
            print("✅ 快捷键监听已启动")
            print("请按 Ctrl+Shift+V 测试，按 Ctrl+C 退出")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 正在停止...")
                manager.stop()
                print("✅ 已停止")
        else:
            print("❌ 启动快捷键监听失败")
    else:
        print("❌ 快捷键功能不可用")