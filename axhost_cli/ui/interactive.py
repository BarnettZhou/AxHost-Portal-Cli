"""交互式组件"""

import asyncio
import sys
from typing import Callable, List, Optional, TypeVar

from prompt_toolkit import PromptSession
from rich.console import Console
from rich.table import Table

from ..models import Project, Tag

T = TypeVar("T")


class InteractiveList:
    """交互式列表组件 - 用于 /projects, /use"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.page_size = 12
    
    async def show(
        self,
        items: List[Project],
        title: str = "项目列表"
    ) -> Optional[Project]:
        """
        显示交互式列表
        
        操作:
        - ↑/↓ 或 j/k: 选择
        - Enter: 确认选择
        - /: 进入搜索模式
        - n/p: 翻页
        - q: 退出
        """
        if not items:
            self.console.print("[yellow]! 没有可显示的项目[/yellow]")
            return None
        
        page = 0
        selected = 0
        search = ""
        filtered_items = items.copy()
        
        # 清除屏幕
        self.console.clear()
        
        while True:
            # 计算分页
            total_pages = max(1, (len(filtered_items) + self.page_size - 1) // self.page_size)
            start = page * self.page_size
            end = start + self.page_size
            page_items = filtered_items[start:end]
            
            # 清除并重新显示
            self.console.clear()
            
            # 渲染并显示表格
            table = self._render_table(page_items, selected - start, title, len(filtered_items), page + 1, total_pages, search)
            self.console.print(table)
            
            # 显示操作提示（使用 Text 对象避免解析问题）
            from rich.text import Text
            hint = Text()
            hint.append("\n")
            hint.append("[↑↓/jk]选择 ", style="dim")
            hint.append("[Enter]进入 ", style="dim")
            hint.append("[/]搜索 ", style="dim")
            hint.append("[n/p]翻页 ", style="dim")
            hint.append("[q]退出", style="dim")
            self.console.print(hint)
            
            # 读取单个按键
            key = await self._read_key()
            
            if key == "UP" or key == "k":
                selected = max(0, selected - 1)
                if selected < page * self.page_size:
                    page = max(0, page - 1)
            
            elif key == "DOWN" or key == "j":
                selected = min(len(filtered_items) - 1, selected + 1)
                if selected >= (page + 1) * self.page_size:
                    page = min(total_pages - 1, page + 1)
            
            elif key == "n":
                if page < total_pages - 1:
                    page += 1
                    selected = page * self.page_size
            
            elif key == "p":
                if page > 0:
                    page -= 1
                    selected = page * self.page_size
            
            elif key == "/":
                # 进入搜索模式
                search = await self._prompt_search()
                if search:
                    filtered_items = [p for p in items if search.lower() in p.name.lower()]
                else:
                    filtered_items = items.copy()
                page = 0
                selected = 0
            
            elif key == "ENTER":
                if 0 <= selected < len(filtered_items):
                    return filtered_items[selected]
            
            elif key == "q" or key == "ESC" or key == "CTRL_C":
                return None
    
    def _render_table(
        self,
        items: List[Project],
        selected: int,
        title: str,
        total: int,
        page: int,
        total_pages: int,
        search: str
    ) -> Table:
        """渲染表格"""
        # 创建主表格
        table = Table(show_header=True, header_style="bold")
        table.add_column("", width=3)
        table.add_column("ID", width=10)
        table.add_column("名称", width=25)
        table.add_column("作者", width=10)
        table.add_column("更新时间", width=12)
        table.add_column("标签", width=15)
        
        for i, project in enumerate(items):
            marker = "🞂" if i == selected else " "
            tags = ", ".join(f"{t.emoji}" for t in project.tags[:3])
            table.add_row(
                marker,
                project.object_id[:8],
                project.name[:24],
                project.author_name[:8],
                project.updated_at.strftime("%m-%d %H:%M"),
                tags
            )
        
        return table
    
    async def _read_key(self) -> str:
        """读取单个按键"""
        try:
            import msvcrt  # Windows
            if msvcrt.kbhit():
                ch = msvcvt.getch()
                if ch == b'\r':
                    return "ENTER"
                elif ch == b'\x1b':
                    return "ESC"
                elif ch == b'q':
                    return "q"
                elif ch == b'j':
                    return "j"
                elif ch == b'k':
                    return "k"
                elif ch == b'n':
                    return "n"
                elif ch == b'p':
                    return "p"
                elif ch == b'/':
                    return "/"
                return ch.decode('utf-8', errors='ignore')
        except ImportError:
            pass
        
        # 使用 prompt_toolkit 读取
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings
        
        bindings = KeyBindings()
        result = None
        
        @bindings.add('up')
        def _(event):
            nonlocal result
            result = "UP"
            event.app.exit()
        
        @bindings.add('down')
        def _(event):
            nonlocal result
            result = "DOWN"
            event.app.exit()
        
        @bindings.add('enter')
        def _(event):
            nonlocal result
            result = "ENTER"
            event.app.exit()
        
        @bindings.add('q')
        def _(event):
            nonlocal result
            result = "q"
            event.app.exit()
        
        @bindings.add('j')
        def _(event):
            nonlocal result
            result = "j"
            event.app.exit()
        
        @bindings.add('k')
        def _(event):
            nonlocal result
            result = "k"
            event.app.exit()
        
        @bindings.add('n')
        def _(event):
            nonlocal result
            result = "n"
            event.app.exit()
        
        @bindings.add('p')
        def _(event):
            nonlocal result
            result = "p"
            event.app.exit()
        
        @bindings.add('/')
        def _(event):
            nonlocal result
            result = "/"
            event.app.exit()
        
        @bindings.add('escape')
        def _(event):
            nonlocal result
            result = "ESC"
            event.app.exit()
        
        @bindings.add('c-c')
        def _(event):
            nonlocal result
            result = "CTRL_C"
            event.app.exit()
        
        session = PromptSession(key_bindings=bindings)
        await session.prompt_async('', refresh_interval=0.1)
        return result or ""
    
    async def _prompt_search(self) -> str:
        """提示搜索输入"""
        self.console.clear()
        self.console.print("\n[bold]搜索模式[/bold]")
        self.console.print("─" * 50)
        session = PromptSession()
        try:
            result = await session.prompt_async("搜索: ")
            return result.strip()
        except (EOFError, KeyboardInterrupt):
            return ""


class InteractiveCreator:
    """交互式创建向导 - 用于 /create"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.session = PromptSession()
    
    async def run(self, existing_tags: Optional[List[Tag]] = None) -> dict:
        """
        运行创建向导
        
        返回: {
            "name": str,
            "remark": str,
            "is_public": bool,
            "view_password": str | None,
            "tag_names": list[str]
        }
        """
        self.console.print("\n[bold]创建新项目[/bold]")
        self.console.print("═" * 50)
        
        # 1. 项目名称
        name = await self._prompt_text("? 项目名称: ", required=True)
        
        # 2. 项目备注
        remark = await self._prompt_text("? 项目备注 (可选): ", required=False)
        
        # 3. 密码保护
        has_password = await self._confirm("? 启用密码保护?", default=False)
        password = None
        is_public = True
        
        if has_password:
            is_public = False
            auto_gen = await self._confirm("  自动生成密码?", default=True)
            if auto_gen:
                import random
                import string
                password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                self.console.print(f"   已自动生成密码: [cyan]{password}[/cyan]")
            else:
                password = await self._prompt_password("  请输入6位密码: ")
        
        # 4. 标签选择
        tag_names = []
        if existing_tags:
            self.console.print("\n? 选择标签 (可多选):")
            for tag in existing_tags:
                if await self._confirm(f"  [{tag.name}]?", default=False):
                    tag_names.append(tag.name)
        
        # 新建标签
        if await self._confirm("? 新建标签?", default=False):
            new_tag = await self._prompt_text("  标签名称: ")
            if new_tag:
                style = await self._select_emoji()
                tag_names.append(new_tag)
                self.console.print(f"   已添加标签: [{style}] {new_tag}")
        
        self.console.print("═" * 50)
        
        return {
            "name": name,
            "remark": remark,
            "is_public": is_public,
            "view_password": password,
            "tag_names": tag_names
        }
    
    async def _prompt_text(self, prompt: str, required: bool = True) -> str:
        """提示文本输入"""
        while True:
            try:
                result = await self.session.prompt_async(prompt)
                result = result.strip()
                if required and not result:
                    self.console.print("[red]此项为必填[/red]")
                    continue
                return result
            except (EOFError, KeyboardInterrupt):
                return ""
    
    async def _prompt_password(self, prompt: str) -> str:
        """提示密码输入"""
        while True:
            try:
                result = await self.session.prompt_async(prompt, is_password=True)
                result = result.strip()
                if len(result) != 6 or not result.isalnum():
                    self.console.print("[red]密码必须为6位字母数字组合[/red]")
                    continue
                return result
            except (EOFError, KeyboardInterrupt):
                return ""
    
    async def _confirm(self, prompt: str, default: bool = False) -> bool:
        """提示确认"""
        suffix = " [Y/n]: " if default else " [y/N]: "
        try:
            result = await self.session.prompt_async(prompt + suffix)
            result = result.strip().lower()
            if not result:
                return default
            return result in ('y', 'yes', '是', '1', 'true')
        except (EOFError, KeyboardInterrupt):
            return default
    
    async def _select_emoji(self) -> str:
        """选择标签颜色/样式"""
        styles = [
            ("default", "默认"),
            ("primary", "主要"),
            ("success", "成功"),
            ("warning", "警告"),
            ("danger", "危险"),
            ("info", "信息"),
        ]
        
        self.console.print("\n  选择标签样式:")
        for i, (key, name) in enumerate(styles, 1):
            self.console.print(f"    {i}. {name}")
        
        try:
            result = await self.session.prompt_async("\n  选择 (1-6): ")
            if result.isdigit():
                idx = int(result) - 1
                if 0 <= idx < len(styles):
                    return styles[idx][0]
        except (EOFError, KeyboardInterrupt):
            pass
        
        return "default"


class InteractiveEditor:
    """交互式编辑向导 - 用于 /edit"""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.session = PromptSession()
    
    async def run(self, project: Project, existing_tags: Optional[List[Tag]] = None) -> Optional[dict]:
        """
        运行编辑向导
        
        返回: 修改后的数据字典，或 None 表示取消
        """
        self.console.print(f"\n编辑项目: {project.name}")
        self.console.print("═" * 50)
        
        # 1. 项目名称
        name = await self._prompt_text_with_default("? 项目名称", project.name)
        
        # 2. 项目备注
        remark = await self._prompt_text_with_default("? 项目备注", project.remark)
        
        # 3. 密码保护
        current_has_password = project.view_password is not None
        has_password = await self._confirm("? 启用密码保护?", default=current_has_password)
        
        password = project.view_password
        is_public = project.is_public
        
        if has_password:
            is_public = False
            if current_has_password:
                self.console.print(f"   当前密码: {'*' * len(project.view_password)}")
                change = await self._confirm("  修改密码?", default=False)
                if change:
                    new_pass = await self._prompt_password("  新密码 (直接回车自动生成): ")
                    if new_pass:
                        password = new_pass
                    else:
                        import random
                        import string
                        password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                        self.console.print(f"   已自动生成新密码: [cyan]{password}[/cyan]")
            else:
                # 从无密码改为有密码
                auto_gen = await self._confirm("  自动生成密码?", default=True)
                if auto_gen:
                    import random
                    import string
                    password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                    self.console.print(f"   已自动生成密码: [cyan]{password}[/cyan]")
                else:
                    password = await self._prompt_password("  请输入6位密码: ")
        else:
            # 移除密码保护
            if current_has_password:
                self.console.print("[yellow]! 将移除密码保护，项目变为公开访问[/yellow]")
                confirm = await self._confirm("  确认?", default=False)
                if not confirm:
                    return None
            password = None
            is_public = True
        
        # 4. 标签
        current_tag_names = [t.name for t in project.tags]
        tag_names = current_tag_names.copy()
        
        if existing_tags:
            self.console.print("\n? 编辑标签:")
            tag_names = []
            for tag in existing_tags:
                default = tag.name in current_tag_names
                if await self._confirm(f"  [{tag.name}]?", default=default):
                    tag_names.append(tag.name)
        
        self.console.print("═" * 50)
        
        # 确认保存
        if not await self._confirm("? 确认保存修改?", default=True):
            return None
        
        return {
            "name": name,
            "remark": remark,
            "is_public": is_public,
            "view_password": password,
            "tag_names": tag_names
        }
    
    async def _prompt_text_with_default(self, prompt: str, default: str) -> str:
        """提示文本输入（带默认值）"""
        display_default = default[:20] + "..." if len(default) > 23 else default
        full_prompt = f"{prompt} [{display_default}]: "
        
        try:
            result = await self.session.prompt_async(full_prompt)
            result = result.strip()
            return result if result else default
        except (EOFError, KeyboardInterrupt):
            return default
    
    async def _prompt_password(self, prompt: str) -> str:
        """提示密码输入"""
        try:
            result = await self.session.prompt_async(prompt, is_password=True)
            result = result.strip()
            if not result:
                return ""
            if len(result) != 6 or not result.isalnum():
                self.console.print("[red]密码必须为6位字母数字组合[/red]")
                return ""
            return result
        except (EOFError, KeyboardInterrupt):
            return ""
    
    async def _confirm(self, prompt: str, default: bool = False) -> bool:
        """提示确认"""
        suffix = " [Y/n]: " if default else " [y/N]: "
        try:
            result = await self.session.prompt_async(prompt + suffix)
            result = result.strip().lower()
            if not result:
                return default
            return result in ('y', 'yes', '是', '1', 'true')
        except (EOFError, KeyboardInterrupt):
            return default
