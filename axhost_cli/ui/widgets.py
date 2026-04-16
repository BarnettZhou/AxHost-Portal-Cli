"""UI 组件"""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

console = Console()

# 跨平台符号定义
SYMBOLS = {
    "success": "[green]✓[/green]",
    "error": "[red]✗[/red]",
    "warning": "[yellow]![/yellow]",
    "info": "[blue]·[/blue]",
    "bullet": "·",
    "arrow": ">",
    "session": "[*]",
    "sync": "[~]",
    "link": "[@]",
    "project": "[#]",
}


def format_time(dt: datetime) -> str:
    """格式化时间"""
    if dt is None:
        return "未知"
    
    now = datetime.now()
    delta = now - dt
    
    if delta.days == 0:
        if delta.seconds < 60:
            return "刚刚"
        elif delta.seconds < 3600:
            return f"{delta.seconds // 60}分钟前"
        else:
            return f"{delta.seconds // 3600}小时前"
    elif delta.days == 1:
        return "昨天"
    elif delta.days < 7:
        return f"{delta.days}天前"
    else:
        return dt.strftime("%Y-%m-%d")


def print_success(message: str) -> None:
    """打印成功消息"""
    console.print(SYMBOLS['success'], escape(message))


def print_error(message: str) -> None:
    """打印错误消息"""
    console.print(SYMBOLS['error'], escape(message))


def print_warning(message: str) -> None:
    """打印警告消息"""
    console.print(SYMBOLS['warning'], escape(message))


def print_info(message: str) -> None:
    """打印信息"""
    console.print(SYMBOLS['info'], escape(message))


def create_session_panel(
    project_name: str,
    linked_dir: Optional[str] = None,
    updated_at: Optional[datetime] = None,
    commands: Optional[list] = None
) -> Panel:
    """创建 Session 信息面板"""
    text = Text()
    
    text.append("Session: ", style="bold")
    text.append(project_name, style="cyan")
    
    if linked_dir:
        text.append(" | 关联: ", style="bold")
        text.append(linked_dir, style="green")
    else:
        text.append(" | 关联: ", style="bold")
        text.append("(未设置)", style="dim")
    
    if updated_at:
        text.append(" | 最后更新: ", style="bold")
        text.append(format_time(updated_at), style="yellow")
    
    if commands:
        text.append(f"\n\n命令: ", style="bold dim")
        text.append(" ".join(f"/{cmd}" for cmd in commands), style="dim")
    
    return Panel(text, border_style="blue")


def create_project_detail_panel(project, linked_dir: Optional[str] = None) -> Panel:
    """创建项目详情面板"""
    text = Text()
    
    text.append(f"项目详情: {project.name}\n", style="bold")
    text.append("-" * 40 + "\n")
    
    text.append("  基本信息:\n", style="bold")
    text.append(f"    ID:         {project.object_id}\n")
    text.append(f"    名称:       {project.name}\n")
    text.append(f"    作者:       {project.author_name}\n")
    created_str = project.created_at.strftime('%Y-%m-%d %H:%M') if project.created_at else "未知"
    updated_str = project.updated_at.strftime('%Y-%m-%d %H:%M') if project.updated_at else "未知"
    text.append(f"    创建时间:   {created_str}\n")
    text.append(f"    最后修改:   {updated_str}\n")
    
    text.append("\n  访问设置:\n", style="bold")
    text.append(f"    公开访问:   {'是' if project.is_public else '否'}\n")
    if project.view_password:
        text.append(f"    访问密码:   {project.view_password}\n")
    
    if project.tags:
        text.append("\n  标签:\n", style="bold")
        for tag in project.tags:
            # 使用标签名称代替 emoji
            text.append(f"    [{tag.name}]\n")
    
    if linked_dir:
        text.append("\n  本地关联:\n", style="bold")
        text.append(f"    关联目录:   {linked_dir}\n")
    
    text.append("\n  线上地址:\n", style="bold")
    text.append(f"    预览链接已生成\n")
    
    return Panel(text, border_style="green")
