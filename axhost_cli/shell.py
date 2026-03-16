"""交互式 Shell 核心"""

import shlex
import webbrowser
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markup import escape

from .api.client import AxHostClient
from .config import CONFIG_DIR, Config
from .models import Project
from .services.auth import AuthService
from .services.batch_sync import BatchSyncService
from .services.project import ProjectService
from .services.upload import UploadService
from .ui.interactive import InteractiveCreator, InteractiveEditor, InteractiveList
from .ui.widgets import (
    create_project_detail_panel,
    create_session_panel,
    format_time,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from .completer import CommandCompleter

# 确保配置目录存在
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = CONFIG_DIR / "history"


class CLIMode(Enum):
    """CLI 模式"""
    GLOBAL = "global"
    SESSION = "session"


class CommandMode(Enum):
    """命令可用模式"""
    GLOBAL = "global"
    SESSION = "session"
    BOTH = "both"


class Command:
    """命令定义"""
    
    def __init__(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        usage: str = "",
        examples: Optional[List[str]] = None,
        mode: CommandMode = CommandMode.BOTH
    ):
        self.name = name
        self.handler = handler
        self.description = description
        self.usage = usage
        self.examples = examples or []
        self.mode = mode


class AxHostShell:
    """AxHost 交互式 Shell"""
    
    def __init__(self):
        self.console = Console()
        self.config = Config.load()
        self.api = AxHostClient(self.config.server_url)
        self.auth = AuthService(self.config, self.api)
        self.project_service = ProjectService(self.api, self.config)
        self.upload_service = UploadService(self.api)
        self.batch_sync = BatchSyncService(self.api, self.config, self.project_service)
        
        self.mode = CLIMode.GLOBAL
        self.current_project: Optional[Project] = None
        self.running = True
        self._last_projects: List[Project] = []
        
        # 初始化命令注册表
        self.commands: Dict[str, Command] = {}
        self._register_commands()
        
        # 初始化 prompt_toolkit
        style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'session': '#00aaaa bold',
        })
        
        self.session = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            completer=CommandCompleter(self),
            style=style,
            enable_suspend=True,
        )
    
    def _register_commands(self):
        """注册命令"""
        # 全局命令
        self._add_cmd("host", self.cmd_host, "设置或查看服务器地址", "/host [url]", ["/host http://localhost:8000"], CommandMode.GLOBAL)
        self._add_cmd("login", self.cmd_login, "登录 (浏览器或账号密码)", "/login [--password]", ["/login", "/login --password"], CommandMode.GLOBAL)
        self._add_cmd("logout", self.cmd_logout, "退出登录", "/logout", ["/logout"], CommandMode.BOTH)
        self._add_cmd("use", self.cmd_use, "搜索并进入项目 Session", "/use [name]", ["/use 官网", "/use"], CommandMode.GLOBAL)
        self._add_cmd("create", self.cmd_create, "交互式创建新项目", "/create", ["/create"], CommandMode.GLOBAL)
        self._add_cmd("projects", self.cmd_projects, "交互式浏览项目列表", "/projects", ["/projects"], CommandMode.GLOBAL)
        self._add_cmd("sync-all", self.cmd_sync_all, "批量同步有更新的项目", "/sync-all", ["/sync-all"], CommandMode.BOTH)
        self._add_cmd("help", self.cmd_help, "查看帮助信息", "/help [command]", ["/help", "/help use"], CommandMode.BOTH)
        
        # Session 命令
        self._add_cmd("link", self.cmd_link, "关联本地目录", "/link <path>", ["/link ./dist"], CommandMode.SESSION)
        self._add_cmd("sync", self.cmd_sync, "同步文件到线上", "/sync", ["/sync"], CommandMode.SESSION)
        self._add_cmd("rename", self.cmd_rename, "重命名项目", "/rename <new_name>", ["/rename 新名称"], CommandMode.SESSION)
        self._add_cmd("edit", self.cmd_edit, "交互式编辑项目", "/edit", ["/edit"], CommandMode.SESSION)
        self._add_cmd("info", self.cmd_info, "查看项目详情", "/info", ["/info"], CommandMode.SESSION)
        self._add_cmd("view", self.cmd_view, "浏览器打开预览", "/view", ["/view"], CommandMode.SESSION)
        self._add_cmd("delete", self.cmd_delete, "删除项目", "/delete", ["/delete"], CommandMode.SESSION)
        
        # 退出命令
        self._add_cmd("exit", self.cmd_exit, "退出当前 Session，返回全局模式", "/exit", ["/exit"], CommandMode.BOTH)
        self._add_cmd("bye", self.cmd_bye, "退出 AxHost CLI", "/bye", ["/bye"], CommandMode.BOTH)
    
    def _add_cmd(self, name: str, handler: Callable, description: str, usage: str, examples: List[str], mode: CommandMode):
        """添加命令"""
        self.commands[name] = Command(name, handler, description, usage, examples, mode)
    
    def get_prompt(self) -> str:
        """获取提示符"""
        if self.mode == CLIMode.SESSION and self.current_project:
            name = self.current_project.name[:15]
            return f"[{name}]> "
        return "axhost> "
    
    async def run(self):
        """主循环"""
        self.print_welcome()
        
        # 尝试加载用户信息
        if self.auth.is_authenticated():
            await self.auth.load_user()
            user = self.auth.get_current_user()
            if user:
                print_success(f"欢迎回来，{user.name}")
        
        while self.running:
            try:
                with patch_stdout():
                    text = await self.session.prompt_async(
                        self.get_prompt(),
                        refresh_interval=0.5
                    )
                await self.execute(text)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
    
    def print_welcome(self):
        """打印欢迎信息"""
        self.console.print("\n[bold]AxHost CLI v0.1.0[/bold]")
        self.console.print("-" * 50)
        
        if self.mode == CLIMode.GLOBAL:
            self.console.print("\n[dim]全局命令:[/dim]")
            global_cmds = [f"/{cmd.name}" for cmd in self.commands.values() if cmd.mode in (CommandMode.GLOBAL, CommandMode.BOTH)]
            self.console.print(f"   {' '.join(global_cmds)}")
        else:
            self.show_session_info()
        
        self.console.print("\n[dim]提示: 使用 Tab 键自动补全，/help 查看详细帮助[/dim]\n")
    
    def show_session_info(self):
        """显示 Session 信息"""
        if not self.current_project:
            return
        
        linked = self.config.get_linked_dir(self.current_project.object_id) or "(未设置)"
        updated = self.config.get_last_sync(self.current_project.object_id)
        updated_str = format_time(updated) if updated else "从未"
        
        session_cmds = [cmd.name for cmd in self.commands.values() if cmd.mode in (CommandMode.SESSION, CommandMode.BOTH)]
        
        # 简洁的文本显示，不使用 Panel（转义变量中的特殊字符）
        self.console.print()
        self.console.print(f"[dim]Session:[/dim] [cyan]{escape(self.current_project.name)}[/cyan] | [dim]关联:[/dim] {escape(linked)} | [dim]更新:[/dim] {escape(updated_str)}")
        self.console.print(f"[dim]命令:[/dim] {' '.join(f'/{cmd}' for cmd in session_cmds[:8])}")
        self.console.print()
    
    async def execute(self, text: str):
        """执行命令"""
        import os
        
        text = text.strip()
        if not text:
            return
        
        # 解析命令
        # Windows 上使用 posix=False，避免反斜杠被当作转义字符
        parts = shlex.split(text, posix=os.name == 'posix')
        cmd_name = parts[0].lstrip('/').lower()
        args = parts[1:]
        
        # 查找命令
        cmd = self.commands.get(cmd_name)
        if not cmd:
            print_error(f"未知命令: /{cmd_name}")
            print_info("输入 /help 查看可用命令")
            return
        
        # 检查命令是否在当前模式可用
        if self.mode == CLIMode.GLOBAL and cmd.mode == CommandMode.SESSION:
            print_warning("请先使用 /use 进入项目")
            return
        
        # 执行命令
        try:
            await cmd.handler(args)
            
            # Session 模式下自动显示 Session 信息
            if self.mode == CLIMode.SESSION and cmd_name not in ('info', 'exit', 'quit', 'help'):
                self.console.print()
                self.show_session_info()
        except Exception as e:
            print_error(f"命令执行失败: {e}")
    
    # ========== 全局命令 ==========
    
    async def cmd_host(self, args: List[str]):
        """设置服务器地址"""
        if not args:
            print_info(f"当前服务器: {self.config.server_url}")
            return
        
        url = args[0]
        
        # 确保 URL 有协议前缀
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        
        # 尝试连接检查
        with self.console.status("[bold green]检查服务器..."):
            is_ok = await self.api.check_server(url)
        
        if is_ok:
            self.config.server_url = url
            self.api.set_base_url(url)
            self.config.save()
            print_success(f"服务器地址已设置为: {url}")
        else:
            # 询问是否强制设置
            from prompt_toolkit import PromptSession
            self.console.print(f"[yellow]! 无法连接到服务器: {url}[/yellow]")
            self.console.print("[dim]   可能原因: 服务未启动、网络不通或缺少 /api/health 端点[/dim]")
            
            try:
                confirm = await PromptSession().prompt_async('是否仍要设置此地址? [y/N]: ')
                if confirm.strip().lower() in ('y', 'yes'):
                    self.config.server_url = url
                    self.api.set_base_url(url)
                    self.config.save()
                    print_success(f"服务器地址已设置为: {url}")
                else:
                    print_info("已取消设置")
            except (EOFError, KeyboardInterrupt):
                print_info("已取消")
    
    async def cmd_login(self, args: List[str]):
        """登录命令：支持浏览器登录或账号密码登录"""
        # 检查是否使用密码登录
        use_password = "-p" in args or "--password" in args
        
        if use_password:
            # 账号密码登录
            await self._login_with_password()
        else:
            # 浏览器登录
            self.console.print("[dim]· 打开浏览器进行登录...[/dim]")
            result = await self.auth.login_with_browser()
            
            if result.success:
                print_success(f"登录成功，欢迎 {result.user.name}")
            else:
                print_error(result.error_message or "登录失败")
    
    async def _login_with_password(self):
        """交互式账号密码登录"""
        import asyncio
        import getpass
        from prompt_toolkit import PromptSession
        
        try:
            # 输入工号/账号
            session = PromptSession()
            employee_id = await session.prompt_async("工号/账号: ")
            
            if not employee_id.strip():
                print_warning("账号不能为空")
                return
            
            # 输入密码（隐藏输入）- 使用 getpass 在后台线程运行
            self.console.print("密码: ", end="")
            password = await asyncio.to_thread(getpass.getpass, "")
            
            if not password:
                print_warning("密码不能为空")
                return
            
            # 执行登录
            with self.console.status("[bold green]正在登录..."):
                result = await self.auth.login_with_credentials(
                    employee_id.strip(), 
                    password
                )
            
            if result.success:
                print_success(f"登录成功，欢迎 {result.user.name}")
            else:
                print_error(result.error_message or "登录失败")
                
        except KeyboardInterrupt:
            print_info("\n已取消登录")
        except Exception as e:
            print_error(f"登录失败: {e}")
    
    async def cmd_logout(self, args: List[str]):
        """退出登录"""
        self.auth.logout()
        print_success("已退出登录")
    
    async def cmd_use(self, args: List[str]):
        """进入项目 Session - 动态从 API 搜索"""
        if args:
            # 搜索模式
            search = args[0]
            try:
                with self.console.status("[bold green]正在搜索项目..."):
                    projects = await self.project_service.search(search)
            except Exception as e:
                print_error(f"搜索失败: {e}")
                return
            
            if not projects:
                print_warning(f"未找到匹配 '{search}' 的项目")
                return
            
            if len(projects) == 1:
                self.enter_session(projects[0])
            else:
                # 显示选择列表
                selector = InteractiveList(self.console)
                selected = await selector.show(projects, f"搜索结果: '{search}'")
                if selected:
                    self.enter_session(selected)
        else:
            # 无参数：进入交互式项目列表
            await self.cmd_projects([])
    
    async def cmd_create(self, args: List[str]):
        """创建项目"""
        # 获取现有标签
        try:
            tags = await self.api.list_tags()
        except Exception:
            tags = []
        
        # 交互式创建
        creator = InteractiveCreator(self.console)
        data = await creator.run(tags)
        
        if not data.get("name"):
            print_error("项目名称不能为空")
            return
        
        with self.console.status("[bold green]创建项目..."):
            project = await self.project_service.create_project(**data)
        
        print_success(f"项目创建成功: {project.name} ({project.object_id})")
        
        # 自动进入 Session
        self.enter_session(project)
    
    async def cmd_projects(self, args: List[str]):
        """项目列表"""
        with self.console.status("[bold green]加载项目列表..."):
            projects = await self.project_service.list_projects(per_page=100)
        
        if not projects:
            print_info("暂无项目，使用 /create 创建新项目")
            return
        
        self._last_projects = projects
        
        # 显示交互式列表
        selector = InteractiveList(self.console)
        selected = await selector.show(projects, "项目列表")
        if selected:
            self.enter_session(selected)
    
    async def cmd_sync_all(self, args: List[str]):
        """批量同步"""
        await self._do_sync_all()
    
    async def _do_sync_all(self):
        """执行批量同步"""
        self.console.print("\n[bold]批量同步检测[/bold]")
        self.console.print("-" * 60)
        
        linked_count = self.batch_sync.get_linked_count()
        if linked_count == 0:
            print_warning("没有关联的目录，请先使用 /link 关联项目")
            return
        
        # 扫描待同步项目
        with self.console.status("[bold green]扫描关联项目..."):
            pending = await self.batch_sync.scan_pending_syncs()
        
        print_info(f"扫描关联项目... 发现 {linked_count} 个关联目录")
        
        if not pending:
            print_success("所有项目均已是最新状态，无需更新\n")
            return
        
        # 显示待同步列表
        self.console.print(f"\n检测到 [bold]{len(pending)}[/bold] 个项目文件待更新:\n")
        self.console.print(self.batch_sync.format_pending_list(pending))
        
        # 确认
        from prompt_toolkit import PromptSession
        confirm = await PromptSession().prompt_async("\n? 是否现在更新? [y/N]: ")
        if confirm.strip().lower() not in ('y', 'yes'):
            print_warning("已取消批量同步\n")
            return
        
        # 执行批量同步
        results = await self.batch_sync.batch_sync(pending)
        
        # 显示汇总
        success_count = sum(1 for r in results if r.success)
        self.console.print(f"\n[bold]═" * 60)
        if success_count == len(results):
            print_success(f"批量同步完成！已更新 {success_count} 个项目\n")
        else:
            print_warning(f"批量同步完成：{success_count}/{len(results)} 个成功\n")
    
    async def cmd_help(self, args: List[str]):
        """帮助"""
        if args:
            cmd_name = args[0].lstrip('/')
            cmd = self.commands.get(cmd_name)
            if cmd:
                self.console.print(f"\n[bold]/{cmd.name}[/bold] - {cmd.description}")
                self.console.print(f"用法: {cmd.usage}")
                if cmd.examples:
                    self.console.print("示例:")
                    for ex in cmd.examples:
                        self.console.print(f"  {ex}")
            else:
                print_error(f"未知命令: {cmd_name}")
            return
        
        # 显示所有可用命令
        self.console.print("\n[bold]AxHost CLI 命令帮助[/bold]\n")
        
        self.console.print("全局命令:")
        for cmd in self.commands.values():
            if cmd.mode in (CommandMode.GLOBAL, CommandMode.BOTH):
                self.console.print(f"  [cyan]/{cmd.name:<12}[/cyan] {cmd.description}")
        
        if self.mode == CLIMode.SESSION:
            self.console.print("\nSession 命令:")
            for cmd in self.commands.values():
                if cmd.mode in (CommandMode.SESSION, CommandMode.BOTH) and cmd.name not in ('exit', 'quit', 'sync-all', 'logout', 'help'):
                    self.console.print(f"  [green]/{cmd.name:<12}[/green] {cmd.description}")
    
    async def cmd_exit(self, args: List[str]):
        """退出 Session"""
        if self.mode == CLIMode.SESSION:
            self.exit_session()
            print_info("已返回全局模式")
        else:
            print_info("提示: 使用 /bye 退出 AxHost CLI")
    
    async def cmd_bye(self, args: List[str]):
        """退出 CLI"""
        self.running = False
        print_info("再见!")
    
    # ========== Session 命令 ==========
    
    async def cmd_link(self, args: List[str]):
        """关联本地目录"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        if not args:
            current = self.config.get_linked_dir(self.current_project.object_id)
            if current:
                print_info(f"当前关联: {current}")
            else:
                print_warning("未关联目录")
            return
        
        from pathlib import Path
        path = Path(args[0]).resolve()
        
        if not path.exists():
            print_error(f"路径不存在: {path}")
            return
        
        if not path.is_dir():
            print_error(f"不是目录: {path}")
            return
        
        self.config.set_linked_dir(self.current_project.object_id, str(path))
        self.config.save()
        print_success(f"已关联: {path}")
    
    async def cmd_sync(self, args: List[str]):
        """同步文件"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        linked = self.config.get_linked_dir(self.current_project.object_id)
        if not linked:
            print_warning("未关联目录，请先使用 /link <path>")
            return
        
        result = await self.upload_service.sync(linked, self.current_project.object_id)
        
        if result.success:
            self.config.set_last_sync(self.current_project.object_id)
            self.config.save()
            print_success("同步完成!")
            if result.url:
                self.console.print(f"   URL: {result.url}")
        else:
            print_error(f"同步失败: {result.error_message}")
    
    async def cmd_rename(self, args: List[str]):
        """重命名项目"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        if not args:
            print_error("请提供新名称: /rename <new_name>")
            return
        
        new_name = args[0]
        old_name = self.current_project.name
        
        # 确认
        from prompt_toolkit import PromptSession
        confirm = await PromptSession().prompt_async(f'确认将 "{old_name}" 重命名为 "{new_name}"? [y/N]: ')
        if confirm.strip().lower() not in ('y', 'yes'):
            print_warning("已取消")
            return
        
        try:
            project = await self.project_service.update_project(
                self.current_project.object_id,
                name=new_name
            )
            self.current_project = project
            print_success("重命名成功")
        except Exception as e:
            print_error(f"重命名失败: {e}")
    
    async def cmd_edit(self, args: List[str]):
        """编辑项目"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        # 获取现有标签
        try:
            tags = await self.api.list_tags()
        except Exception:
            tags = []
        
        # 交互式编辑
        editor = InteractiveEditor(self.console)
        data = await editor.run(self.current_project, tags)
        
        if not data:
            print_warning("已取消编辑")
            return
        
        try:
            project = await self.project_service.update_project(
                self.current_project.object_id,
                **data
            )
            self.current_project = project
            print_success("项目已更新")
        except Exception as e:
            print_error(f"更新失败: {e}")
    
    async def cmd_info(self, args: List[str]):
        """项目详情"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        linked = self.config.get_linked_dir(self.current_project.object_id)
        panel = create_project_detail_panel(self.current_project, linked)
        self.console.print(panel)
        
        # 显示预览 URL
        url = self.upload_service.get_preview_url(self.current_project.object_id)
        self.console.print(f"\n预览地址: {url}")
    
    async def cmd_view(self, args: List[str]):
        """浏览器打开"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        url = self.upload_service.get_preview_url(self.current_project.object_id)
        self.console.print(f"[dim]· 正在打开浏览器...[/dim]\n   {url}")
        webbrowser.open(url)
    
    async def cmd_delete(self, args: List[str]):
        """删除项目"""
        if not self.current_project:
            print_error("未进入项目 Session")
            return
        
        self.console.print(f"\n[red]! 警告: 即将删除项目 \"{escape(self.current_project.name)}\"[/red]")
        self.console.print("[red]   此操作不可恢复！[/red]\n")
        
        # 必须输入 "Yes" 确认
        from prompt_toolkit import PromptSession
        confirm = await PromptSession().prompt_async('请输入 "Yes" 确认删除: ')
        
        if confirm.strip() != "Yes":
            print_warning("已取消删除")
            return
        
        with self.console.status("[bold red]正在删除..."):
            success = await self.project_service.delete_project(self.current_project.object_id)
        
        if success:
            print_success("项目已删除")
            self.exit_session()
        else:
            print_error("删除失败")
    
    # ========== 辅助方法 ==========
    
    def enter_session(self, project: Project):
        """进入 Session 模式"""
        self.current_project = project
        self.project_service.set_current(project)
        self.mode = CLIMode.SESSION
        
        print_success(f"进入项目: {project.name}")
        self.show_session_info()
    
    def exit_session(self):
        """退出 Session 模式"""
        self.current_project = None
        self.project_service.set_current(None)
        self.mode = CLIMode.GLOBAL
