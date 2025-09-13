"""
系统托盘管理器
使用pystray创建系统托盘图标和菜单
"""
import pystray
from pystray import MenuItem, Menu
from PIL import Image, ImageDraw
import threading
from typing import Optional, Callable


class SystemTrayManager:
    def __init__(self, app_name: str = "Crypto Clipboard"):
        self.app_name = app_name
        self.icon = None
        self.running = False
        
        # 回调函数
        self.on_show_window: Optional[Callable[[], None]] = None
        self.on_toggle_encryption: Optional[Callable[[], None]] = None
        self.on_toggle_auto_decrypt: Optional[Callable[[], None]] = None
        self.on_manual_encrypt: Optional[Callable[[], None]] = None
        self.on_manual_decrypt: Optional[Callable[[], None]] = None
        self.on_exit: Optional[Callable[[], None]] = None
        
        # 状态
        self.encryption_enabled = False
        self.auto_decrypt_enabled = True
        self.password_set = False
        
    def create_icon_image(self, color: str = "blue") -> Image.Image:
        """创建托盘图标"""
        # 创建一个简单的图标
        width = height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # 绘制一个锁的图标
        # 外框
        draw.rectangle([10, 20, 54, 54], outline=color, width=3)
        
        # 锁扣
        draw.arc([20, 10, 44, 30], start=0, end=180, fill=color, width=3)
        
        # 锁孔
        draw.ellipse([28, 32, 36, 40], fill=color)
        
        return image
    
    def create_menu(self) -> Menu:
        """创建托盘菜单"""
        menu_items = [
            MenuItem(
                "显示窗口", 
                self._show_window,
                default=True
            ),
            Menu.SEPARATOR,
            MenuItem(
                f"自动加密: {'开' if self.encryption_enabled else '关'}", 
                self._toggle_encryption,
                enabled=self.password_set
            ),
            MenuItem(
                f"自动解密: {'开' if self.auto_decrypt_enabled else '关'}", 
                self._toggle_auto_decrypt,
                enabled=self.password_set
            ),
            Menu.SEPARATOR,
            MenuItem(
                "手动加密剪贴板", 
                self._manual_encrypt,
                enabled=self.password_set
            ),
            MenuItem(
                "手动解密剪贴板", 
                self._manual_decrypt,
                enabled=self.password_set
            ),
            Menu.SEPARATOR,
            MenuItem("退出", self._exit_app)
        ]
        
        return Menu(*menu_items)
    
    def start(self):
        """启动系统托盘"""
        if self.running:
            return
        
        self.running = True
        
        # 创建图标
        icon_color = "green" if self.password_set else "gray"
        icon_image = self.create_icon_image(icon_color)
        
        self.icon = pystray.Icon(
            self.app_name,
            icon_image,
            menu=self.create_menu()
        )
        
        # 在单独的线程中运行托盘
        self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self.tray_thread.start()
    
    def stop(self):
        """停止系统托盘"""
        self.running = False
        if self.icon:
            self.icon.stop()
    
    def _run_tray(self):
        """运行托盘图标"""
        try:
            self.icon.run()
        except Exception as e:
            print(f"托盘运行错误: {e}")
    
    def update_status(self, password_set: bool, encryption_enabled: bool, auto_decrypt_enabled: bool):
        """更新状态"""
        self.password_set = password_set
        self.encryption_enabled = encryption_enabled
        self.auto_decrypt_enabled = auto_decrypt_enabled
        
        if self.icon:
            # 更新图标颜色
            icon_color = "green" if password_set else "gray"
            self.icon.icon = self.create_icon_image(icon_color)
            
            # 更新菜单
            self.icon.menu = self.create_menu()
    
    def show_notification(self, title: str, message: str):
        """显示通知"""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                print(f"通知显示失败: {e}")
    
    def _show_window(self, icon=None, item=None):
        """显示主窗口"""
        if self.on_show_window:
            self.on_show_window()
    
    def _toggle_encryption(self, icon=None, item=None):
        """切换自动加密"""
        if self.on_toggle_encryption:
            self.on_toggle_encryption()
    
    def _toggle_auto_decrypt(self, icon=None, item=None):
        """切换自动解密"""
        if self.on_toggle_auto_decrypt:
            self.on_toggle_auto_decrypt()
    
    def _manual_encrypt(self, icon=None, item=None):
        """手动加密"""
        if self.on_manual_encrypt:
            self.on_manual_encrypt()
    
    def _manual_decrypt(self, icon=None, item=None):
        """手动解密"""
        if self.on_manual_decrypt:
            self.on_manual_decrypt()
    
    def _exit_app(self, icon=None, item=None):
        """退出应用"""
        if self.on_exit:
            self.on_exit()


# 测试代码
if __name__ == "__main__":
    import time
    
    def test_show_window():
        print("显示窗口")
    
    def test_toggle_encryption():
        print("切换自动加密")
        tray.encryption_enabled = not tray.encryption_enabled
        tray.update_status(True, tray.encryption_enabled, tray.auto_decrypt_enabled)
    
    def test_toggle_auto_decrypt():
        print("切换自动解密")
        tray.auto_decrypt_enabled = not tray.auto_decrypt_enabled
        tray.update_status(True, tray.encryption_enabled, tray.auto_decrypt_enabled)
    
    def test_manual_encrypt():
        print("手动加密")
        tray.show_notification("加密完成", "剪贴板内容已加密")
    
    def test_manual_decrypt():
        print("手动解密")
        tray.show_notification("解密完成", "剪贴板内容已解密")
    
    def test_exit():
        print("退出应用")
        tray.stop()
    
    # 创建托盘管理器
    tray = SystemTrayManager()
    
    # 设置回调函数
    tray.on_show_window = test_show_window
    tray.on_toggle_encryption = test_toggle_encryption
    tray.on_toggle_auto_decrypt = test_toggle_auto_decrypt
    tray.on_manual_encrypt = test_manual_encrypt
    tray.on_manual_decrypt = test_manual_decrypt
    tray.on_exit = test_exit
    
    # 启动托盘
    print("启动系统托盘...")
    tray.start()
    
    # 模拟状态变化
    time.sleep(2)
    print("设置密码...")
    tray.update_status(True, False, True)
    
    try:
        # 保持运行
        while tray.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在退出...")
        tray.stop()