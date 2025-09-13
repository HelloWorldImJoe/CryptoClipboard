"""
权限管理器 - 跨平台权限检测和请求
处理macOS辅助功能权限、Windows管理员权限等
"""
import os
import sys
import platform
import subprocess
import ctypes
import webbrowser
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PermissionManager:
    """跨平台权限管理器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_admin = self._check_admin_rights()
        
    def _check_admin_rights(self) -> bool:
        """检查是否具有管理员权限"""
        try:
            if self.system == "windows":
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            elif self.system == "darwin":  # macOS
                return os.geteuid() == 0
            else:  # Linux
                return os.geteuid() == 0
        except Exception as e:
            logger.warning(f"无法检查管理员权限: {e}")
            return False
    
    def check_accessibility_permission(self) -> bool:
        """检查辅助功能权限（主要针对macOS）"""
        if self.system != "darwin":
            return True  # 其他系统不需要此权限
            
        try:
            # macOS 检测辅助功能权限
            script = '''
            tell application "System Events"
                set ui_enabled to UI elements enabled
            end tell
            return ui_enabled
            '''
            
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            return result.returncode == 0 and result.stdout.strip() == "true"
        except Exception as e:
            logger.error(f"检查辅助功能权限失败: {e}")
            return False
    
    def request_accessibility_permission(self) -> bool:
        """请求辅助功能权限"""
        if self.system != "darwin":
            return True
            
        try:
            # 显示权限请求对话框
            self._show_macos_permission_dialog()
            
            # 尝试打开系统偏好设置
            subprocess.run([
                'open', 
                'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'
            ], check=False)
            
            return True
        except Exception as e:
            logger.error(f"请求辅助功能权限失败: {e}")
            return False
    
    def _show_macos_permission_dialog(self):
        """显示macOS权限设置对话框（命令行版本）"""
        message = """CryptoCP 需要辅助功能权限来使用全局快捷键功能。

请按照以下步骤操作：

1. 打开系统偏好设置 > 安全性与隐私 > 隐私 > 辅助功能
2. 点击锁图标并输入密码
3. 找到并勾选 Python 或终端应用
4. 重新启动 CryptoCP

是否现在打开系统偏好设置？(y/n): """
        
        try:
            response = input(message).strip().lower()
            return response in ['y', 'yes', '是']
        except (EOFError, KeyboardInterrupt):
            return False
    
    def check_windows_admin(self) -> bool:
        """检查Windows管理员权限"""
        if self.system != "windows":
            return True
            
        return self.is_admin
    
    def request_windows_admin(self) -> bool:
        """请求Windows管理员权限（重启应用）"""
        if self.system != "windows":
            return True
            
        if self.is_admin:
            return True
            
        try:
            # 显示提示对话框
            self._show_windows_admin_dialog()
            
            # 尝试以管理员身份重启
            script = sys.executable
            params = ' '.join(sys.argv)
            
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                script, 
                params, 
                None, 
                1
            )
            
            # 退出当前进程
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"请求管理员权限失败: {e}")
            return False
    
    def _show_windows_admin_dialog(self):
        """显示Windows管理员权限对话框（命令行版本）"""
        message = """CryptoCP 需要管理员权限来注册全局快捷键。

将会重新启动应用并请求管理员权限。
如果出现UAC提示，请点击"是"。

是否继续？(y/n): """
        
        try:
            response = input(message).strip().lower()
            return response in ['y', 'yes', '是']
        except (EOFError, KeyboardInterrupt):
            return False
    
    def check_all_permissions(self) -> Dict[str, Any]:
        """检查所有必要权限"""
        permissions = {
            "admin": self.is_admin,
            "accessibility": True,
            "system": self.system,
            "can_use_hotkeys": True,
            "issues": []
        }
        
        if self.system == "darwin":
            # macOS 需要辅助功能权限
            permissions["accessibility"] = self.check_accessibility_permission()
            if not permissions["accessibility"]:
                permissions["can_use_hotkeys"] = False
                permissions["issues"].append("需要辅助功能权限")
                
        elif self.system == "windows":
            # Windows 建议管理员权限
            if not self.is_admin:
                permissions["issues"].append("建议使用管理员权限")
                
        return permissions
    
    def request_all_permissions(self) -> bool:
        """请求所有必要权限"""
        permissions = self.check_all_permissions()
        
        if permissions["can_use_hotkeys"]:
            return True
            
        success = True
        
        if self.system == "darwin" and not permissions["accessibility"]:
            success &= self.request_accessibility_permission()
            
        elif self.system == "windows" and not permissions["admin"]:
            # Windows 仅在需要时请求管理员权限
            success &= self.request_windows_admin()
            
        return success
    
    def get_permission_status_text(self) -> str:
        """获取权限状态描述文本"""
        permissions = self.check_all_permissions()
        
        status_lines = [
            f"操作系统: {permissions['system'].title()}",
            f"管理员权限: {'✅' if permissions['admin'] else '❌'}",
        ]
        
        if self.system == "darwin":
            status_lines.append(
                f"辅助功能权限: {'✅' if permissions['accessibility'] else '❌'}"
            )
            
        status_lines.append(
            f"快捷键功能: {'✅ 可用' if permissions['can_use_hotkeys'] else '❌ 需要权限'}"
        )
        
        if permissions["issues"]:
            status_lines.append("\n问题:")
            for issue in permissions["issues"]:
                status_lines.append(f"  • {issue}")
                
        return "\n".join(status_lines)
    
    def show_permission_help(self, parent=None):
        """显示权限帮助（命令行版本）"""
        help_text = self._get_permission_help_text()
        print("\n权限设置帮助:")
        print("=" * 50)
        print(help_text)
        print("=" * 50)
    
    def _get_permission_help_text(self) -> str:
        """获取权限帮助文本"""
        if self.system == "darwin":
            return """macOS 辅助功能权限设置:

1. 打开"系统偏好设置"
2. 选择"安全性与隐私"
3. 点击"隐私"标签
4. 选择左侧"辅助功能"
5. 点击锁图标并输入密码
6. 勾选 Python 或终端应用
7. 重新启动 CryptoCP

注意: 权限更改可能需要重启应用才能生效。"""
            
        elif self.system == "windows":
            return """Windows 管理员权限设置:

方法一（推荐）:
1. 右键点击应用图标
2. 选择"以管理员身份运行"

方法二:
1. 右键点击应用图标
2. 选择"属性"
3. 选择"兼容性"标签
4. 勾选"以管理员身份运行此程序"

注意: 管理员权限可以确保全局快捷键功能正常工作。"""
            
        else:  # Linux
            return """Linux 权限设置:

通常情况下 Linux 不需要特殊权限。

如果遇到问题，请尝试:

1. 确保安装了必要的包:
   sudo apt-get install python3-tk python3-dev

2. 检查 X11 权限:
   xhost +local:

3. 使用 sudo 运行（不推荐）:
   sudo python3 cli_main.py

注意: 建议在普通用户权限下运行。"""


class PermissionTest:
    """权限测试工具"""
    
    def __init__(self):
        self.permission_manager = PermissionManager()
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """运行全面的权限测试"""
        results = {
            "timestamp": self._get_timestamp(),
            "system_info": self._get_system_info(),
            "permissions": self.permission_manager.check_all_permissions(),
            "tests": {}
        }
        
        # 测试基本权限
        results["tests"]["basic_permissions"] = self._test_basic_permissions()
        
        # 测试快捷键功能
        results["tests"]["hotkey_capability"] = self._test_hotkey_capability()
        
        # 测试权限请求功能
        results["tests"]["permission_request"] = self._test_permission_request()
        
        return results
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        return {
            "system": platform.system(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_version": platform.python_version()
        }
    
    def _test_basic_permissions(self) -> Dict[str, Any]:
        """测试基本权限"""
        try:
            permissions = self.permission_manager.check_all_permissions()
            return {
                "status": "success",
                "admin": permissions["admin"],
                "accessibility": permissions["accessibility"],
                "can_use_hotkeys": permissions["can_use_hotkeys"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _test_hotkey_capability(self) -> Dict[str, Any]:
        """测试快捷键功能可用性"""
        try:
            # 尝试导入 pynput
            import pynput
            from pynput import keyboard
            
            # 检查是否可以创建监听器
            def dummy_callback():
                pass
            
            listener = keyboard.Listener(on_press=dummy_callback)
            listener.start()
            listener.stop()
            
            return {
                "status": "success",
                "pynput_available": True,
                "listener_creation": True
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "pynput_available": False
            }
    
    def _test_permission_request(self) -> Dict[str, Any]:
        """测试权限请求功能"""
        try:
            # 只测试功能可用性，不实际请求权限
            system = platform.system().lower()
            
            if system == "darwin":
                available = hasattr(subprocess, 'run')
            elif system == "windows":
                available = hasattr(ctypes.windll, 'shell32')
            else:
                available = True
                
            return {
                "status": "success",
                "available": available,
                "system": system
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def print_test_results(self, results: Dict[str, Any]):
        """打印测试结果"""
        print("🧪 权限测试结果")
        print("=" * 50)
        print(f"时间: {results['timestamp']}")
        print(f"系统: {results['system_info']['system']} {results['system_info']['version']}")
        print(f"Python: {results['system_info']['python_version']}")
        print()
        
        # 权限状态
        permissions = results['permissions']
        print("📋 权限状态:")
        print(f"  管理员权限: {'✅' if permissions['admin'] else '❌'}")
        print(f"  辅助功能权限: {'✅' if permissions['accessibility'] else '❌'}")
        print(f"  快捷键功能: {'✅' if permissions['can_use_hotkeys'] else '❌'}")
        
        if permissions['issues']:
            print("  问题:")
            for issue in permissions['issues']:
                print(f"    • {issue}")
        print()
        
        # 测试结果
        for test_name, test_result in results['tests'].items():
            status = "✅" if test_result['status'] == 'success' else "❌"
            print(f"{status} {test_name}: {test_result['status']}")
            
            if test_result['status'] == 'error':
                print(f"    错误: {test_result['error']}")
        
        print()
        print("💡 建议:")
        if not permissions['can_use_hotkeys']:
            if permissions['system'] == 'darwin':
                print("  • 在系统偏好设置中启用辅助功能权限")
            elif permissions['system'] == 'windows':
                print("  • 以管理员身份运行应用")
            print("  • 重新启动应用以应用权限更改")
        else:
            print("  • 所有权限已正确配置，快捷键功能应该正常工作")


if __name__ == "__main__":
    # 运行权限测试
    tester = PermissionTest()
    results = tester.run_comprehensive_test()
    tester.print_test_results(results)
    
    # 显示权限管理器状态
    pm = PermissionManager()
    print("\n" + "=" * 50)
    print("🔐 权限管理器状态:")
    print(pm.get_permission_status_text())