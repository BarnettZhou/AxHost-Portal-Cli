"""认证服务"""

import asyncio
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse

import keyring

from ..api.client import AxHostClient
from ..config import Config
from ..models import AuthResult, User


SERVICE_NAME = "axhost-cli"
USERNAME = "api_token"


class SecureStorage:
    """安全存储"""
    
    @staticmethod
    def save_token(token: str) -> None:
        """保存 Token 到系统密钥环"""
        keyring.set_password(SERVICE_NAME, USERNAME, token)
    
    @staticmethod
    def get_token() -> Optional[str]:
        """从系统密钥环获取 Token"""
        return keyring.get_password(SERVICE_NAME, USERNAME)
    
    @staticmethod
    def delete_token() -> None:
        """删除 Token"""
        try:
            keyring.delete_password(SERVICE_NAME, USERNAME)
        except keyring.errors.PasswordDeleteError:
            pass


class AuthService:
    """认证服务"""
    
    def __init__(self, config: Config, client: AxHostClient):
        self.config = config
        self.client = client
        self._user: Optional[User] = None
        
        # 尝试加载已保存的 Token
        saved_token = SecureStorage.get_token()
        if saved_token:
            self.client.set_token(saved_token)
    
    async def login_with_browser(self, timeout: int = 120) -> AuthResult:
        """
        浏览器自动登录（本地回调方案）
        
        流程:
        1. 启动临时 HTTP 服务器
        2. 打开浏览器访问登录页
        3. 等待回调接收 Token
        4. 验证并保存
        """
        # 1. 生成 state 防 CSRF
        state = secrets.token_urlsafe(32)
        received_token: Optional[str] = None
        received_state: Optional[str] = None
        
        # 2. 创建回调处理器
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal received_token, received_state
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                if parsed.path == '/callback':
                    received_token = params.get('token', [None])[0]
                    received_state = params.get('state', [None])[0]
                    
                    # 返回成功页面
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write('''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>登录成功</title>
                        <style>
                            body { font-family: system-ui; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
                            .box { text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }
                            .icon { font-size: 64px; margin-bottom: 20px; }
                            h1 { margin: 0 0 10px; color: #333; }
                            p { color: #666; margin: 0; }
                        </style>
                    </head>
                    <body>
                        <div class="box">
                            <div class="icon">OK</div>
                            <h1>登录成功</h1>
                            <p>请返回 CLI 查看结果</p>
                        </div>
                    </body>
                    </html>
                    '''.encode('utf-8'))
                    
                    # 关闭服务器
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
            
            def log_message(self, format, *args):
                pass  # 禁用日志
        
        # 3. 启动临时 HTTP 服务器
        server = HTTPServer(('127.0.0.1', 0), CallbackHandler)
        port = server.server_address[1]
        
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # 4. 构造登录 URL
        from urllib.parse import quote
        callback_url = f"http://127.0.0.1:{port}/callback"
        login_url = f"{self.config.server_url}/auth/cli-login?callback={quote(callback_url)}&state={state}"
        
        # 5. 打开浏览器
        webbrowser.open(login_url)
        
        # 6. 等待回调或超时
        import time
        from rich.console import Console
        from rich.status import Status
        
        console = Console()
        start_time = time.time()
        
        try:
            with Status("[dim]· 等待授权...[/dim] (按 Ctrl+C 取消)", console=console) as status:
                while time.time() - start_time < timeout:
                    if received_token is not None:
                        break
                    await asyncio.sleep(0.1)
            
            if received_token is None:
                return AuthResult(success=False, error_message="登录超时")
            
            # 7. 验证 state
            if received_state != state:
                return AuthResult(success=False, error_message="安全验证失败 (state mismatch)")
            
            # 8. 验证并保存 Token
            return await self.verify_token(received_token)
            
        except KeyboardInterrupt:
            return AuthResult(success=False, error_message="登录已取消")
        finally:
            server.shutdown()
    
    async def verify_token(self, token: str) -> AuthResult:
        """验证并保存令牌"""
        try:
            # 设置临时 token 用于验证请求
            self.client.set_token(token)
            user = await self.client.get_current_user()
            SecureStorage.save_token(token)
            self._user = user
            return AuthResult(success=True, access_token=token, user=user)
        except Exception as e:
            return AuthResult(success=False, error_message=f"验证失败: {e}")
    
    async def login_with_credentials(self, employee_id: str, password: str) -> AuthResult:
        """使用工号和密码登录"""
        try:
            result = await self.client.login(employee_id, password)
            token = result.get("access_token")
            user_data = result.get("user")
            
            if token and user_data:
                self.client.set_token(token)
                SecureStorage.save_token(token)
                self._user = User.from_dict(user_data)
                return AuthResult(
                    success=True,
                    access_token=token,
                    user=self._user
                )
            
            return AuthResult(success=False, error_message="登录失败: 无效的响应")
        except Exception as e:
            return AuthResult(success=False, error_message=f"登录失败: {e}")
    
    def is_authenticated(self) -> bool:
        """检查是否已登录"""
        return SecureStorage.get_token() is not None
    
    def get_current_user(self) -> Optional[User]:
        """获取当前用户"""
        return self._user
    
    async def load_user(self) -> Optional[User]:
        """加载当前用户信息"""
        if not self.is_authenticated():
            return None
        try:
            self._user = await self.client.get_current_user()
            return self._user
        except Exception:
            return None
    
    def logout(self) -> None:
        """退出登录"""
        self._user = None
        self.client.set_token("")
        SecureStorage.delete_token()
