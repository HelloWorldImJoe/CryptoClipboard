#!/usr/bin/env python3
"""
Crypto Clipboard - 命令行版本
不依赖GUI组件，适用于没有tkinter的环境
"""

import sys
import os
import threading
import time
import signal
import getpass
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from crypto_manager import CryptoManager
    from clipboard_manager import ClipboardManager
    from config_manager import ConfigManager, AppSettings
    from direct_paste_manager import SmartPasteManager
    from permission_manager import PermissionManager
    try:
        from system_tray import SystemTrayManager
        TRAY_AVAILABLE = True
    except ImportError:
        print("⚠️  系统托盘功能不可用（缺少pystray或PIL）")
        TRAY_AVAILABLE = False
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保安装了核心依赖: pip install cryptography pyperclip")
    sys.exit(1)


class CryptoClipboardCLI:
    def __init__(self):
        self.crypto_manager = CryptoManager()
        self.config_manager = ConfigManager()
        self.settings = AppSettings(self.config_manager)
        self.clipboard_manager = ClipboardManager(self.crypto_manager)
        self.system_tray = None
        self.permission_manager = PermissionManager()
        
        # 应用状态
        self.running = True
        self.password_set = False
        
        self._setup_components()
        self._load_saved_settings()
    
    def _setup_components(self):
        """设置各个组件"""
        # 设置剪贴板管理器回调
        self.clipboard_manager.on_clipboard_changed = self._on_clipboard_changed
        self.clipboard_manager.on_encryption_performed = self._on_encryption_performed
        self.clipboard_manager.on_decryption_performed = self._on_decryption_performed
        self.clipboard_manager.on_error = self._on_error
        
        # 创建系统托盘（如果可用）
        if TRAY_AVAILABLE:
            try:
                self.system_tray = SystemTrayManager()
                
                # 设置托盘回调
                self.system_tray.on_toggle_encryption = self._toggle_encryption_from_tray
                self.system_tray.on_toggle_auto_decrypt = self._toggle_auto_decrypt_from_tray
                self.system_tray.on_manual_encrypt = self._manual_encrypt_from_tray
                self.system_tray.on_manual_decrypt = self._manual_decrypt_from_tray
                self.system_tray.on_exit = self._on_exit
                
                print("✅ 系统托盘功能已启用")
            except Exception as e:
                print(f"⚠️  系统托盘启动失败: {e}")
                self.system_tray = None
        
        # 创建智能粘贴管理器
        try:
            self.smart_paste_manager = SmartPasteManager(
                self.crypto_manager,
                self.config_manager
            )
            
            if self.smart_paste_manager.is_available():
                print("🎯 智能粘贴功能已启用")
            else:
                print("⚠️  智能粘贴功能不可用（需要pynput库）")
                self.smart_paste_manager = None
                
        except Exception as e:
            print(f"⚠️  智能粘贴管理器启动失败: {e}")
            self.smart_paste_manager = None
    
    def _load_saved_settings(self):
        """加载保存的设置"""
        try:
            # 检查是否有保存的密钥
            if self.config_manager.has_saved_key():
                print("🔑 检测到已保存的密钥")
                self._prompt_for_saved_password()
            
            # 加载其他设置
            self.clipboard_manager.enable_encryption(self.settings.encryption_enabled)
            self.clipboard_manager.enable_auto_decrypt(self.settings.auto_decrypt_enabled)
            
        except Exception as e:
            print(f"⚠️  加载设置失败: {e}")
    
    def _prompt_for_saved_password(self):
        """提示用户输入保存的密码"""
        for attempt in range(3):
            try:
                password = getpass.getpass("请输入密码: ")
                
                if self.config_manager.verify_password(password):
                    self._set_password_with_saved_key(password)
                    return
                else:
                    print(f"❌ 密码不正确 ({attempt + 1}/3)")
            except KeyboardInterrupt:
                print("\n取消密码输入")
                return
        
        print("❌ 密码验证失败次数过多，使用新密码")
    
    def _set_password_with_saved_key(self, password: str):
        """使用保存的密钥设置密码"""
        try:
            key_data = self.config_manager.load_key_data()
            if key_data:
                self.crypto_manager.set_password(password, key_data['salt'])
                self.password_set = True
                print("✅ 密码验证成功，已恢复会话")
                self._update_tray_status()
                self._start_monitoring()
        except Exception as e:
            print(f"❌ 恢复密钥失败: {e}")
    
    def _start_monitoring(self):
        """开始监控剪贴板"""
        if self.password_set:
            self.clipboard_manager.start_monitoring()
            print("🔍 开始监控剪贴板")
    
    def _stop_monitoring(self):
        """停止监控剪贴板"""
        self.clipboard_manager.stop_monitoring()
        print("⏹️  停止监控剪贴板")
    
    def _update_tray_status(self):
        """更新托盘状态"""
        if self.system_tray:
            self.system_tray.update_status(
                self.password_set,
                self.settings.encryption_enabled,
                self.settings.auto_decrypt_enabled
            )
    
    # 回调函数
    def _on_clipboard_changed(self, old_content: str, new_content: str):
        """剪贴板变化回调"""
        print(f"📋 剪贴板变化: {len(new_content)} 字符")
    
    def _on_encryption_performed(self, original_text: str):
        """加密执行回调"""
        print(f"🔐 已加密文本 ({len(original_text)} 字符)")
        
        if self.system_tray and self.settings.show_notifications:
            self.system_tray.show_notification("加密完成", "剪贴板内容已加密")
    
    def _on_decryption_performed(self, decrypted_text: str):
        """解密执行回调"""
        print(f"🔓 已解密文本 ({len(decrypted_text)} 字符)")
        
        if self.system_tray and self.settings.show_notifications:
            self.system_tray.show_notification("解密完成", "剪贴板内容已解密")
    
    def _on_error(self, error_message: str):
        """错误回调"""
        print(f"❌ 错误: {error_message}")
    
    def _on_exit(self):
        """退出应用回调"""
        self.running = False
    
    # 托盘回调函数
    def _toggle_encryption_from_tray(self):
        """从托盘切换加密状态"""
        if self.password_set:
            current = self.settings.encryption_enabled
            self.settings.encryption_enabled = not current
            self.clipboard_manager.enable_encryption(self.settings.encryption_enabled)
            
            status = "启用" if self.settings.encryption_enabled else "禁用"
            print(f"🔄 自动加密已{status}")
            
            self._update_tray_status()
    
    def _toggle_auto_decrypt_from_tray(self):
        """从托盘切换自动解密状态"""
        if self.password_set:
            current = self.settings.auto_decrypt_enabled
            self.settings.auto_decrypt_enabled = not current
            self.clipboard_manager.enable_auto_decrypt(self.settings.auto_decrypt_enabled)
            
            status = "启用" if self.settings.auto_decrypt_enabled else "禁用"
            print(f"🔄 自动解密已{status}")
            
            self._update_tray_status()
    
    def _manual_encrypt_from_tray(self):
        """从托盘手动加密"""
        if self.password_set:
            success = self.clipboard_manager.manual_encrypt()
            if success:
                print("🔐 手动加密完成（托盘）")
    
    def _manual_decrypt_from_tray(self):
        """从托盘手动解密"""
        if self.password_set:
            success = self.clipboard_manager.manual_decrypt()
            if success:
                print("🔓 手动解密完成（托盘）")
    
    def set_password(self, password: str) -> bool:
        """设置密码"""
        try:
            if len(password) < 6:
                print("❌ 密码长度至少为6位")
                return False
            
            salt = self.crypto_manager.set_password(password)
            key_hash = self.crypto_manager.generate_key_hash(password, salt)
            
            # 保存密钥数据
            self.config_manager.save_key_data(salt, key_hash)
            
            self.password_set = True
            print("✅ 密码设置成功")
            self._update_tray_status()
            self._start_monitoring()
            return True
            
        except Exception as e:
            print(f"❌ 设置密码失败: {e}")
            return False
    
    def toggle_encryption(self) -> bool:
        """切换自动加密"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        enabled = not self.settings.encryption_enabled
        self.settings.encryption_enabled = enabled
        self.clipboard_manager.enable_encryption(enabled)
        self._update_tray_status()
        
        status = "启用" if enabled else "禁用"
        print(f"🔄 自动加密已{status}")
        return True
    
    def toggle_auto_decrypt(self) -> bool:
        """切换自动解密（已弃用，剪贴板始终保持加密）"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        print("ℹ️  自动解密功能已禁用")
        print("🔒 剪贴板现在始终保持加密状态，以确保安全")
        print("💡 使用以下命令临时访问内容:")
        print("   - temp-decrypt (td): 临时解密10秒")
        print("   - peek (pk): 预览内容不修改剪贴板")
        print("   - manual-decrypt (md): 永久解密")
        return True
    
    def manual_encrypt(self) -> bool:
        """手动加密"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        return self.clipboard_manager.manual_encrypt()
    
    def manual_decrypt(self) -> bool:
        """手动解密"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        return self.clipboard_manager.manual_decrypt()
    
    def temporary_decrypt(self) -> bool:
        """临时解密"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        duration = self.settings.temporary_decrypt_duration
        print(f"⏰ 临时解密剪贴板内容（{duration}秒后自动重新加密）...")
        return self.clipboard_manager.temporary_decrypt(duration)
    
    def temporary_decrypt_with_duration(self, duration: int) -> bool:
        """带指定时间的临时解密"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return False
        
        if not (5 <= duration <= 300):
            print("❌ 时间必须在5-300秒之间")
            return False
        
        print(f"⏰ 临时解密剪贴板内容（{duration}秒后自动重新加密）...")
        return self.clipboard_manager.temporary_decrypt(duration)
    
    def set_temporary_decrypt_time(self):
        """设置默认临时解密时间"""
        try:
            current = self.settings.temporary_decrypt_duration
            print(f"📐 当前默认临时解密时间: {current}秒")
            
            while True:
                try:
                    user_input = input("请输入新的默认时间（5-300秒，回车取消）: ").strip()
                    if not user_input:
                        print("❌ 已取消设置")
                        return
                    
                    new_duration = int(user_input)
                    self.settings.temporary_decrypt_duration = new_duration
                    print(f"✅ 默认临时解密时间已设置为: {new_duration}秒")
                    break
                    
                except ValueError as e:
                    if "必须在5-300秒之间" in str(e):
                        print("❌ 时间必须在5-300秒之间，请重新输入")
                    else:
                        print("❌ 请输入有效的数字")
                except KeyboardInterrupt:
                    print("\n❌ 已取消设置")
                    return
                    
        except Exception as e:
            print(f"❌ 设置失败: {e}")
    
    def toggle_hotkey(self):
        """切换快捷键功能"""
        if not self.smart_paste_manager or not self.smart_paste_manager.is_available():
            print("❌ 快捷键功能不可用（需要安装pynput库）")
            return
        
        # 检查权限
        permissions = self.permission_manager.check_all_permissions()
        if not permissions["can_use_hotkeys"]:
            print("❌ 快捷键功能需要系统权限")
            print("\n📋 权限状态:")
            print(self.permission_manager.get_permission_status_text())
            
            # 询问是否请求权限
            try:
                response = input("\n是否现在请求必要权限？(y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    print("🔧 请求权限中...")
                    if self.permission_manager.request_all_permissions():
                        print("✅ 权限请求成功，请重新启动应用")
                    else:
                        print("❌ 权限请求失败")
                        self._show_permission_help()
                else:
                    print("❌ 未授予权限，快捷键功能无法使用")
                    self._show_permission_help()
            except KeyboardInterrupt:
                print("\n❌ 用户取消")
            return
        
        current_status = self.settings.hotkey_enabled
        new_status = not current_status
        
        self.settings.hotkey_enabled = new_status
        
        if new_status:
            # 启用快捷键
            if self.smart_paste_manager.initialize():
                print(f"✅ 快捷键功能已启用: {self.settings.hotkey_combination}")
                print("🎯 现在可以使用快捷键解密并直接粘贴内容了")
            else:
                print("❌ 快捷键启用失败，可能需要权限设置")
                self.settings.hotkey_enabled = False
                self._show_permission_help()
        else:
            # 禁用快捷键
            self.smart_paste_manager.disable_hotkey()
            print("❌ 快捷键功能已禁用")
    
    def set_hotkey(self):
        """设置快捷键组合"""
        if not self.smart_paste_manager or not self.smart_paste_manager.is_available():
            print("❌ 快捷键功能不可用（需要安装pynput库）")
            return
        
        print(f"当前快捷键: {self.settings.hotkey_combination}")
        print("\n快捷键格式示例:")
        print("  ctrl+shift+v    - Ctrl + Shift + V")
        print("  cmd+alt+d       - Cmd + Alt + D") 
        print("  ctrl+shift+f1   - Ctrl + Shift + F1")
        
        new_hotkey = input("\n请输入新的快捷键组合: ").strip().lower()
        
        if not new_hotkey:
            print("❌ 快捷键不能为空")
            return
        
        try:
            # 验证快捷键格式
            if self._validate_hotkey_format(new_hotkey):
                old_hotkey = self.settings.hotkey_combination
                self.settings.hotkey_combination = new_hotkey
                
                # 如果当前启用了快捷键，需要重新初始化
                if self.settings.hotkey_enabled:
                    self.smart_paste_manager.disable_hotkey()
                    if self.smart_paste_manager.initialize():
                        print(f"✅ 快捷键已更改为: {new_hotkey}")
                    else:
                        # 恢复原来的设置
                        self.settings.hotkey_combination = old_hotkey
                        self.smart_paste_manager.initialize()
                        print("❌ 新快捷键设置失败，已恢复原设置")
                else:
                    print(f"✅ 快捷键已设置为: {new_hotkey}")
                    print("💡 使用 'hotkey' 命令启用快捷键功能")
            else:
                print("❌ 无效的快捷键格式")
                
        except Exception as e:
            print(f"❌ 设置快捷键失败: {e}")
    
    def test_hotkey(self):
        """测试快捷键功能"""
        if not self.smart_paste_manager or not self.smart_paste_manager.is_available():
            print("❌ 快捷键功能不可用（需要安装pynput库）")
            return
        
        if not self.settings.hotkey_enabled:
            print("❌ 快捷键功能未启用，请先使用 'hotkey' 命令启用")
            return
        
        print("🧪 快捷键功能测试")
        print(f"当前快捷键: {self.settings.hotkey_combination}")
        
        # 测试智能粘贴管理器状态
        status = self.smart_paste_manager.get_status()
        print(f"可用性: {'✅' if status['available'] else '❌'}")
        print(f"快捷键监听: {'✅' if status['hotkey_enabled'] else '❌'}")
        
        if status['available'] and status['hotkey_enabled']:
            print("\n✅ 快捷键功能正常")
            print("🎯 请复制一些文本到剪贴板，然后在任意输入框中按快捷键测试")
        else:
            print("\n❌ 快捷键功能异常")
            if 'config_error' in status:
                print(f"配置错误: {status['config_error']}")
    
    def _validate_hotkey_format(self, hotkey: str) -> bool:
        """验证快捷键格式"""
        try:
            parts = hotkey.split('+')
            if len(parts) < 2:
                return False
            
            valid_modifiers = {'ctrl', 'alt', 'shift', 'cmd', 'meta', 'super'}
            valid_keys = set('abcdefghijklmnopqrstuvwxyz0123456789')
            valid_keys.update([f'f{i}' for i in range(1, 13)])  # F1-F12
            
            modifiers = parts[:-1]
            key = parts[-1]
            
            for modifier in modifiers:
                if modifier not in valid_modifiers:
                    return False
            
            if key not in valid_keys:
                return False
            
            return True
        except:
            return False
    
    def _show_permission_help(self):
        """显示权限设置帮助"""
        import os
        if os.name != 'nt':  # macOS/Linux
            print("\n🔧 权限设置帮助:")
            print("在macOS上需要授予辅助功能权限:")
            print("1. 打开 系统偏好设置")
            print("2. 选择 安全性与隐私")
            print("3. 点击 隐私 标签")
            print("4. 选择 辅助功能")
            print("5. 添加并勾选此应用")
            print("6. 重新启动应用")
    
    def peek_decrypt(self):
        """预览解密内容"""
        if not self.password_set:
            print("❌ 请先设置密码")
            return
        
        content = self.clipboard_manager.peek_decrypt()
        if content:
            print(f"👁️  预览解密内容: {content}")
        else:
            print("❌ 剪贴板为空或无法解密")
    
    def show_status(self):
        """显示当前状态"""
        print("\n📊 当前状态:")
        print(f"  密码设置: {'✅' if self.password_set else '❌'}")
        print(f"  自动加密: {'✅' if self.settings.encryption_enabled else '❌'}")
        print(f"  剪贴板策略: 🔒 始终保持加密状态")
        print(f"  临时解密时间: ⏰ {self.settings.temporary_decrypt_duration}秒")
        print(f"  监控状态: {'🔍 运行中' if self.clipboard_manager.is_running else '⏹️ 已停止'}")
        print(f"  系统托盘: {'✅' if self.system_tray else '❌'}")
        
        # 显示快捷键状态
        if self.smart_paste_manager and self.smart_paste_manager.is_available():
            hotkey_status = "启用" if self.settings.hotkey_enabled else "禁用"
            print(f"  快捷键功能: {'🎯' if self.settings.hotkey_enabled else '❌'} {hotkey_status}")
            if self.settings.hotkey_enabled:
                print(f"  快捷键组合: ⌨️ {self.settings.hotkey_combination}")
        else:
            print(f"  快捷键功能: ❌ 不可用（需要pynput库）")
        
        # 显示剪贴板信息
        info = self.clipboard_manager.get_current_clipboard_info()
        if info['has_content']:
            content_type = "🔐 加密文本" if info['is_encrypted'] else "📝 普通文本"
            print(f"  剪贴板: {content_type} ({info['length']} 字符)")
        else:
            print(f"  剪贴板: 空")
    
    def check_permissions(self):
        """检查系统权限状态"""
        print("🔍 检查系统权限状态...")
        print("=" * 40)
        
        permissions = self.permission_manager.check_all_permissions()
        
        print(f"操作系统: {permissions['system'].title()}")
        print(f"管理员权限: {'✅' if permissions['admin'] else '❌'}")
        
        if permissions['system'] == 'darwin':
            print(f"辅助功能权限: {'✅' if permissions['accessibility'] else '❌'}")
        
        print(f"快捷键功能: {'✅ 可用' if permissions['can_use_hotkeys'] else '❌ 需要权限'}")
        
        if permissions['issues']:
            print("\n⚠️ 发现问题:")
            for issue in permissions['issues']:
                print(f"  • {issue}")
                
            print("\n💡 解决方案:")
            if permissions['system'] == 'darwin' and not permissions['accessibility']:
                print("  • 在系统偏好设置中启用辅助功能权限")
                print("  • 运行 'request-permissions' 命令获取详细指导")
            elif permissions['system'] == 'windows' and not permissions['admin']:
                print("  • 以管理员身份运行应用")
                print("  • 运行 'request-permissions' 命令尝试提权")
        else:
            print("\n✅ 所有权限已正确配置")
    
    def request_permissions(self):
        """请求必要的系统权限"""
        print("🔧 请求系统权限...")
        
        permissions = self.permission_manager.check_all_permissions()
        
        if permissions['can_use_hotkeys']:
            print("✅ 已具有所需权限，无需请求")
            return
        
        print("📋 权限状态:")
        print(self.permission_manager.get_permission_status_text())
        
        try:
            response = input("\n是否继续请求权限？(y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("❌ 用户取消权限请求")
                return
            
            print("🔄 正在请求权限...")
            success = self.permission_manager.request_all_permissions()
            
            if success:
                print("✅ 权限请求完成")
                print("💡 请重新启动应用以应用权限更改")
            else:
                print("❌ 权限请求失败")
                self.permission_manager.show_permission_help()
                
        except KeyboardInterrupt:
            print("\n❌ 用户取消")
    
    def run_interactive(self):
        """运行交互模式"""
        print("🎮 进入交互模式（输入 'help' 查看命令）")
        
        while self.running:
            try:
                command = input("\n> ").strip().lower()
                
                if command == 'help' or command == 'h':
                    self._show_help()
                elif command == 'password' or command == 'p':
                    password = getpass.getpass("请输入新密码: ")
                    self.set_password(password)
                elif command == 'encrypt' or command == 'e':
                    self.toggle_encryption()
                elif command == 'decrypt' or command == 'd':
                    self.toggle_auto_decrypt()
                elif command == 'manual-encrypt' or command == 'me':
                    self.manual_encrypt()
                elif command == 'manual-decrypt' or command == 'md':
                    self.manual_decrypt()
                elif command == 'temp-decrypt' or command == 'td':
                    self.temporary_decrypt()
                elif command.startswith('temp-decrypt ') or command.startswith('td '):
                    # 支持带时间参数的临时解密
                    parts = command.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        duration = int(parts[1])
                        self.temporary_decrypt_with_duration(duration)
                    else:
                        print("❌ 时间参数必须是数字（5-300秒）")
                elif command == 'set-temp-time' or command == 'stt':
                    self.set_temporary_decrypt_time()
                elif command == 'hotkey' or command == 'hk':
                    self.toggle_hotkey()
                elif command == 'set-hotkey' or command == 'shk':
                    self.set_hotkey()
                elif command == 'test-hotkey' or command == 'thk':
                    self.test_hotkey()
                elif command == 'check-permissions' or command == 'cp':
                    self.check_permissions()
                elif command == 'request-permissions' or command == 'rp':
                    self.request_permissions()
                elif command == 'peek' or command == 'pk':
                    self.peek_decrypt()
                elif command == 'status' or command == 's':
                    self.show_status()
                elif command == 'quit' or command == 'q':
                    break
                elif command == '':
                    continue
                else:
                    print(f"❌ 未知命令: {command}")
                    print("输入 'help' 查看可用命令")
                    
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except EOFError:
                print("\n👋 再见！")
                break
        
        self._shutdown()
    
    def _show_help(self):
        """显示帮助信息"""
        current_duration = self.settings.temporary_decrypt_duration
        hotkey_status = "启用" if self.settings.hotkey_enabled else "禁用"
        hotkey_combo = self.settings.hotkey_combination
        print(f"""
📖 可用命令:
  help (h)             - 显示此帮助信息
  password (p)         - 设置/修改密码
  encrypt (e)          - 切换自动加密
  decrypt (d)          - 切换自动解密（已禁用，剪贴板保持加密）
  manual-encrypt (me)  - 手动加密剪贴板
  manual-decrypt (md)  - 永久解密剪贴板
  temp-decrypt (td)    - 临时解密剪贴板（当前默认: {current_duration}秒）
  temp-decrypt N (td N) - 临时解密N秒（例: td 30）
  set-temp-time (stt)  - 设置默认临时解密时间
  hotkey (hk)         - 切换快捷键功能（当前: {hotkey_status}）
  set-hotkey (shk)    - 设置快捷键组合（当前: {hotkey_combo}）
  test-hotkey (thk)   - 测试快捷键功能
  check-permissions (cp) - 检查系统权限状态
  request-permissions (rp) - 请求必要的系统权限
  peek (pk)           - 预览解密内容（不修改剪贴板）
  status (s)          - 显示当前状态
  quit (q)            - 退出应用
        """)
    
    def run_daemon(self):
        """运行守护进程模式"""
        print("🤖 后台守护模式启动")
        print("按 Ctrl+C 退出")
        
        # 启动系统托盘
        if self.system_tray:
            self.system_tray.start()
            self._update_tray_status()
            print("📱 系统托盘已启动")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 收到退出信号")
        
        self._shutdown()
    
    def _shutdown(self):
        """关闭应用"""
        print("🔄 正在关闭应用...")
        self._stop_monitoring()
        
        if self.system_tray:
            self.system_tray.stop()
            print("📱 系统托盘已停止")
        
        print("✅ 应用已安全关闭")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Clipboard - 命令行版本')
    parser.add_argument('--daemon', '-d', action='store_true', 
                       help='后台守护模式运行')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='交互模式运行（默认）')
    
    args = parser.parse_args()
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print("\n🛑 收到退出信号，正在关闭应用...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🔐 Crypto Clipboard - 命令行版本")
    print("=" * 40)
    
    try:
        app = CryptoClipboardCLI()
        
        if args.daemon:
            app.run_daemon()
        else:
            app.run_interactive()
    
    except Exception as e:
        print(f"❌ 应用启动失败: {e}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()