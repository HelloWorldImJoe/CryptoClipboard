"""
Crypto Clipboard - 主应用程序
整合所有组件的主程序（命令行版本）
"""
import sys
import signal
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from crypto_manager import CryptoManager
    from clipboard_manager import ClipboardManager
    from system_tray import SystemTrayManager
    from config_manager import ConfigManager, AppSettings
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保安装了所有依赖: pip install -r requirements.txt")
    sys.exit(1)


class CryptoClipboardApp:
    def __init__(self):
        self.crypto_manager = CryptoManager()
        self.config_manager = ConfigManager()
        self.settings = AppSettings(self.config_manager)
        self.clipboard_manager = ClipboardManager(self.crypto_manager)
        self.system_tray = None
        
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
        
        # 创建系统托盘
        try:
            self.system_tray = SystemTrayManager()
            
            # 设置托盘回调
            self.system_tray.on_show_window = self._show_window
            self.system_tray.on_toggle_encryption = self._toggle_encryption_from_tray
            self.system_tray.on_toggle_auto_decrypt = self._toggle_auto_decrypt_from_tray
            self.system_tray.on_manual_encrypt = self._manual_encrypt_from_tray
            self.system_tray.on_manual_decrypt = self._manual_decrypt_from_tray
            self.system_tray.on_exit = self._on_exit
            
        except ImportError:
            print("系统托盘功能不可用（缺少pystray库）")
            self.system_tray = None
    
    def _load_saved_settings(self):
        """加载保存的设置"""
        try:
            # 检查是否有保存的密钥
            if self.config_manager.has_saved_key():
                # 提示用户输入密码
                self._prompt_for_saved_password()
            
            # 加载其他设置
            self.clipboard_manager.enable_encryption(self.settings.encryption_enabled)
            self.clipboard_manager.enable_auto_decrypt(self.settings.auto_decrypt_enabled)
                
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def _prompt_for_saved_password(self):
        """提示用户输入保存的密码（命令行版本）"""
        import getpass
        
        while True:
            try:
                password = getpass.getpass("检测到已保存的密钥，请输入密码: ")
                
                if not password:  # 用户输入空密码
                    print("密码不能为空")
                    continue
                
                if self.config_manager.verify_password(password):
                    self._set_password_with_saved_key(password)
                    break
                else:
                    print("密码不正确，请重试")
            except KeyboardInterrupt:
                print("\n用户取消输入")
                break
            except Exception as e:
                print(f"输入密码时出错: {e}")
                break
    
    def _set_password_with_saved_key(self, password: str):
        """使用保存的密钥设置密码"""
        try:
            key_data = self.config_manager.load_key_data()
            if key_data:
                self.crypto_manager.set_password(password, key_data['salt'])
                self.password_set = True
                
                print("密码验证成功，已恢复会话")
                
                self._update_tray_status()
                self._start_monitoring()
                
        except Exception as e:
            print(f"恢复密钥失败: {e}")
    
    def _start_monitoring(self):
        """开始监控剪贴板"""
        if self.password_set:
            self.clipboard_manager.start_monitoring()
            print("开始监控剪贴板")
    
    def _stop_monitoring(self):
        """停止监控剪贴板"""
        self.clipboard_manager.stop_monitoring()
        print("停止监控剪贴板")
    
    def _update_tray_status(self):
        """更新托盘状态"""
        if self.system_tray:
            self.system_tray.update_status(
                self.password_set,
                self.settings.encryption_enabled,
                self.settings.auto_decrypt_enabled
            )
    
    def set_password(self, password: str):
        """设置密码（命令行接口）"""
        try:
            salt = self.crypto_manager.set_password(password)
            key_hash = self.crypto_manager.generate_key_hash(password, salt)
            
            # 保存密钥数据
            self.config_manager.save_key_data(salt, key_hash)
            
            self.password_set = True
            self._update_tray_status()
            self._start_monitoring()
            print("密码设置成功")
            
        except Exception as e:
            print(f"设置密码失败: {e}")
            raise e
    
    def toggle_encryption(self):
        """切换加密状态"""
        self.settings.encryption_enabled = not self.settings.encryption_enabled
        self.clipboard_manager.enable_encryption(self.settings.encryption_enabled)
        self._update_tray_status()
        print(f"自动加密已{'启用' if self.settings.encryption_enabled else '禁用'}")
    
    def toggle_auto_decrypt(self):
        """切换自动解密状态"""
        self.settings.auto_decrypt_enabled = not self.settings.auto_decrypt_enabled
        self.clipboard_manager.enable_auto_decrypt(self.settings.auto_decrypt_enabled)
        self._update_tray_status()
        print(f"自动解密已{'启用' if self.settings.auto_decrypt_enabled else '禁用'}")
    
    def manual_encrypt(self):
        """手动加密"""
        success = self.clipboard_manager.manual_encrypt()
        if success:
            print("手动加密完成")
        return success
        
    def manual_decrypt(self):
        """手动解密"""
        success = self.clipboard_manager.manual_decrypt()
        if success:
            print("手动解密完成")
        return success
    
    def _on_exit(self):
        """退出应用回调"""
        self._stop_monitoring()
        
        if self.system_tray:
            self.system_tray.stop()
        
        self.running = False
        print("应用已退出")
    
    # 剪贴板回调函数
    def _on_clipboard_changed(self, old_content: str, new_content: str):
        """剪贴板变化回调"""
        info = self.clipboard_manager.get_current_clipboard_info()
        print(f"剪贴板变化: {'有内容' if info['has_content'] else '空'}, "
              f"{'已加密' if info['is_encrypted'] else '未加密'}, "
              f"长度: {info['length']}")
    
    def _on_encryption_performed(self, original_text: str):
        """加密执行回调"""
        print(f"已加密文本 ({len(original_text)} 字符)")
        
        if self.system_tray and self.settings.show_notifications:
            self.system_tray.show_notification("加密完成", "剪贴板内容已加密")
    
    def _on_decryption_performed(self, decrypted_text: str):
        """解密执行回调"""
        print(f"已解密文本 ({len(decrypted_text)} 字符)")
        
        if self.system_tray and self.settings.show_notifications:
            self.system_tray.show_notification("解密完成", "剪贴板内容已解密")
    
    def _on_error(self, error_message: str):
        """错误回调"""
        print(f"剪贴板错误: {error_message}")
    
    # 托盘回调函数
    def _show_window(self):
        """显示窗口（对于命令行版本无需操作）"""
        print("Crypto Clipboard 正在运行（命令行模式）")
    
    def _toggle_encryption_from_tray(self):
        """从托盘切换加密状态"""
        if self.password_set:
            self.toggle_encryption()
    
    def _toggle_auto_decrypt_from_tray(self):
        """从托盘切换自动解密状态"""
        if self.password_set:
            self.toggle_auto_decrypt()
    
    def _manual_encrypt_from_tray(self):
        """从托盘手动加密"""
        if self.password_set:
            success = self.manual_encrypt()
            if success:
                print("手动加密（托盘）")
    
    def _manual_decrypt_from_tray(self):
        """从托盘手动解密"""
        if self.password_set:
            success = self.manual_decrypt()
            if success:
                print("手动解密（托盘）")
    
    def run(self):
        """运行应用（命令行模式）"""
        try:
            # 启动系统托盘
            if self.system_tray:
                self.system_tray.start()
                self._update_tray_status()
            
            print("Crypto Clipboard 已启动（命令行模式）")
            print("应用将在后台运行，可通过系统托盘操作")
            
            # 保持应用运行
            import time
            while self.running:
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n收到中断信号，正在退出...")
            self._on_exit()
        except Exception as e:
            print(f"应用运行错误: {e}")
            self._on_exit()


def main():
    """主函数"""
    # 设置信号处理
    def signal_handler(signum, frame):
        print("\n收到退出信号，正在关闭应用...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # 创建并运行应用
        app = CryptoClipboardApp()
        app.run()
    
    except Exception as e:
        print(f"应用启动失败: {e}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()