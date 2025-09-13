"""
配置管理器
负责应用配置的持久化存储
"""
import json
import os
import base64
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    def __init__(self, app_name: str = "CryptoClipboard"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.key_file = self.config_dir / "key.dat"
        
        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认配置
        self.default_config = {
            "encryption_enabled": False,
            "auto_decrypt_enabled": True,
            "start_minimized": False,
            "show_notifications": True,
            "auto_start": False,
            "window_position": {"x": 100, "y": 100},
            "window_size": {"width": 500, "height": 600},
            "hotkey": {
                "enabled": False,
                "combination": "ctrl+shift+v",  # 默认快捷键
                "modifier_keys": ["ctrl", "shift"],
                "key": "v"
            }
        }
        
        self.config = self.load_config()
    
    def _get_config_dir(self) -> Path:
        """获取配置目录路径"""
        if os.name == 'nt':  # Windows
            config_dir = Path(os.environ.get('APPDATA', '')) / self.app_name
        else:  # macOS/Linux
            config_dir = Path.home() / f'.{self.app_name.lower()}'
        
        return config_dir
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 合并默认配置，确保所有必要的键都存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                
                return config
            else:
                return self.default_config.copy()
        
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.default_config.copy()
    
    def save_config(self) -> bool:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> bool:
        """设置配置值"""
        self.config[key] = value
        return self.save_config()
    
    def update(self, updates: Dict[str, Any]) -> bool:
        """批量更新配置"""
        self.config.update(updates)
        return self.save_config()
    
    def save_key_data(self, salt: bytes, key_hash: str) -> bool:
        """保存密钥相关数据"""
        try:
            key_data = {
                "salt": base64.b64encode(salt).decode(),
                "key_hash": key_hash
            }
            
            with open(self.key_file, 'w', encoding='utf-8') as f:
                json.dump(key_data, f)
            
            return True
        except Exception as e:
            print(f"保存密钥数据失败: {e}")
            return False
    
    def load_key_data(self) -> Optional[Dict[str, str]]:
        """加载密钥相关数据"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'r', encoding='utf-8') as f:
                    key_data = json.load(f)
                
                # 解码salt
                key_data['salt'] = base64.b64decode(key_data['salt'])
                return key_data
            
            return None
        except Exception as e:
            print(f"加载密钥数据失败: {e}")
            return None
    
    def has_saved_key(self) -> bool:
        """检查是否有保存的密钥数据"""
        return self.key_file.exists()
    
    def verify_password(self, password: str) -> bool:
        """验证密码是否正确"""
        key_data = self.load_key_data()
        if not key_data:
            return False
        
        try:
            # 尝试相对导入，如果失败则使用绝对导入
            try:
                from crypto_manager import CryptoManager
            except ImportError:
                from crypto_manager import CryptoManager
                
            crypto = CryptoManager()
            generated_hash = crypto.generate_key_hash(password, key_data['salt'])
            return generated_hash == key_data['key_hash']
        except Exception as e:
            print(f"密码验证失败: {e}")
            return False
    
    def delete_key_data(self) -> bool:
        """删除密钥数据"""
        try:
            if self.key_file.exists():
                self.key_file.unlink()
            return True
        except Exception as e:
            print(f"删除密钥数据失败: {e}")
            return False
    
    def reset_config(self) -> bool:
        """重置配置为默认值"""
        self.config = self.default_config.copy()
        return self.save_config()
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到文件"""
        try:
            export_data = {
                "config": self.config,
                "has_key": self.has_saved_key(),
                "export_time": str(Path(__file__).stat().st_mtime)
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            if "config" in import_data:
                # 只导入配置，不导入密钥数据
                imported_config = import_data["config"]
                
                # 验证配置项
                for key in imported_config:
                    if key in self.default_config:
                        self.config[key] = imported_config[key]
                
                return self.save_config()
            
            return False
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "config_dir": str(self.config_dir),
            "config_file": str(self.config_file),
            "key_file": str(self.key_file),
            "has_saved_key": self.has_saved_key(),
            "config_size": len(json.dumps(self.config)),
            "total_settings": len(self.config)
        }


# 配置项访问的便捷方法
class AppSettings:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
    
    @property
    def encryption_enabled(self) -> bool:
        return self.config.get("encryption_enabled", False)
    
    @encryption_enabled.setter
    def encryption_enabled(self, value: bool):
        self.config.set("encryption_enabled", value)
    
    @property
    def auto_decrypt_enabled(self) -> bool:
        return self.config.get("auto_decrypt_enabled", False)  # 默认禁用自动解密，保持剪贴板加密
    
    @auto_decrypt_enabled.setter
    def auto_decrypt_enabled(self, value: bool):
        self.config.set("auto_decrypt_enabled", value)
    
    @property
    def start_minimized(self) -> bool:
        return self.config.get("start_minimized", False)
    
    @start_minimized.setter
    def start_minimized(self, value: bool):
        self.config.set("start_minimized", value)
    
    @property
    def show_notifications(self) -> bool:
        return self.config.get("show_notifications", True)
    
    @show_notifications.setter
    def show_notifications(self, value: bool):
        self.config.set("show_notifications", value)
    
    @property
    def temporary_decrypt_duration(self) -> int:
        return self.config.get("temporary_decrypt_duration", 10)  # 默认10秒
    
    @temporary_decrypt_duration.setter
    def temporary_decrypt_duration(self, value: int):
        # 限制在5-300秒之间（5秒到5分钟）
        if 5 <= value <= 300:
            self.config.set("temporary_decrypt_duration", value)
        else:
            raise ValueError("临时解密时间必须在5-300秒之间")
    
    @property
    def auto_start(self) -> bool:
        return self.config.get("auto_start", False)
    
    @auto_start.setter
    def auto_start(self, value: bool):
        self.config.set("auto_start", value)
    
    @property
    def window_position(self) -> Dict[str, int]:
        return self.config.get("window_position", {"x": 100, "y": 100})
    
    @window_position.setter
    def window_position(self, value: Dict[str, int]):
        self.config.set("window_position", value)
    
    @property
    def window_size(self) -> Dict[str, int]:
        return self.config.get("window_size", {"width": 500, "height": 600})
    
    @window_size.setter
    def window_size(self, value: Dict[str, int]):
        self.config.set("window_size", value)
    
    # 快捷键相关属性
    @property
    def hotkey_enabled(self) -> bool:
        """快捷键是否启用"""
        hotkey_config = self.config.get("hotkey", {})
        return hotkey_config.get("enabled", False)
    
    @hotkey_enabled.setter
    def hotkey_enabled(self, value: bool):
        """设置快捷键启用状态"""
        hotkey_config = self.config.get("hotkey", {})
        hotkey_config["enabled"] = value
        self.config.set("hotkey", hotkey_config)
    
    @property
    def hotkey_combination(self) -> str:
        """获取快捷键组合字符串"""
        hotkey_config = self.config.get("hotkey", {})
        return hotkey_config.get("combination", "ctrl+shift+v")
    
    @hotkey_combination.setter 
    def hotkey_combination(self, value: str):
        """设置快捷键组合字符串"""
        if not self._validate_hotkey_combination(value):
            raise ValueError(f"无效的快捷键组合: {value}")
        
        # 解析快捷键组合
        parts = value.lower().split('+')
        key = parts[-1]
        modifiers = parts[:-1]
        
        hotkey_config = self.config.get("hotkey", {})
        hotkey_config["combination"] = value.lower()
        hotkey_config["modifier_keys"] = modifiers
        hotkey_config["key"] = key
        self.config.set("hotkey", hotkey_config)
    
    @property
    def hotkey_modifiers(self) -> list:
        """获取快捷键修饰键列表"""
        hotkey_config = self.config.get("hotkey", {})
        return hotkey_config.get("modifier_keys", ["ctrl", "shift"])
    
    @property
    def hotkey_key(self) -> str:
        """获取快捷键主键"""
        hotkey_config = self.config.get("hotkey", {})
        return hotkey_config.get("key", "v")
    
    def _validate_hotkey_combination(self, combination: str) -> bool:
        """验证快捷键组合的有效性"""
        if not combination or not isinstance(combination, str):
            return False
        
        parts = combination.lower().split('+')
        if len(parts) < 2:  # 至少需要一个修饰键+一个主键
            return False
        
        valid_modifiers = {'ctrl', 'alt', 'shift', 'cmd', 'meta', 'super'}
        valid_keys = {
            # 字母
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
            'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
            # 数字
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            # 功能键
            'f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12',
            # 特殊键
            'space', 'enter', 'tab', 'esc', 'escape', 'backspace', 'delete',
            'home', 'end', 'page_up', 'page_down', 'up', 'down', 'left', 'right'
        }
        
        modifiers = parts[:-1]
        key = parts[-1]
        
        # 检查修饰键
        for modifier in modifiers:
            if modifier not in valid_modifiers:
                return False
        
        # 检查主键
        if key not in valid_keys:
            return False
        
        return True
    
    def get_hotkey_display_text(self) -> str:
        """获取用于显示的快捷键文本"""
        if not self.hotkey_enabled:
            return "未设置"
        
        combination = self.hotkey_combination
        # 为macOS转换显示文本
        if os.name != 'nt':  # macOS/Linux
            combination = combination.replace('ctrl', '⌘').replace('alt', '⌥').replace('shift', '⇧')
        else:  # Windows
            combination = combination.replace('ctrl', 'Ctrl').replace('alt', 'Alt').replace('shift', 'Shift')
        
        return combination.title()


# 测试代码
if __name__ == "__main__":
    # 创建配置管理器
    config_manager = ConfigManager("TestCryptoClipboard")
    settings = AppSettings(config_manager)
    
    print("配置信息:")
    info = config_manager.get_config_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    print("\n当前配置:")
    print(f"  加密启用: {settings.encryption_enabled}")
    print(f"  自动解密: {settings.auto_decrypt_enabled}")
    print(f"  最小化启动: {settings.start_minimized}")
    print(f"  显示通知: {settings.show_notifications}")
    
    # 测试设置
    print("\n测试配置设置...")
    settings.encryption_enabled = True
    settings.start_minimized = True
    
    print("设置后的配置:")
    print(f"  加密启用: {settings.encryption_enabled}")
    print(f"  最小化启动: {settings.start_minimized}")
    
    # 测试密钥数据
    print("\n测试密钥数据...")
    test_salt = b"test_salt_12345"
    test_hash = "test_hash_12345"
    
    success = config_manager.save_key_data(test_salt, test_hash)
    print(f"保存密钥数据: {'成功' if success else '失败'}")
    
    key_data = config_manager.load_key_data()
    print(f"加载密钥数据: {key_data is not None}")
    
    if key_data:
        print(f"  Salt匹配: {key_data['salt'] == test_salt}")
        print(f"  Hash匹配: {key_data['key_hash'] == test_hash}")
    
    # 清理测试数据
    config_manager.delete_key_data()
    print("已清理测试数据")