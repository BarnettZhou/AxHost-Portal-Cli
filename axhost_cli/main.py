"""主程序入口"""

import asyncio
import sys

import click
from rich.console import Console

from .shell import AxHostShell

console = Console()


@click.command()
@click.version_option(version="0.1.0", prog_name="axhost")
@click.option('--server', '-s', help='服务器地址')
@click.option('--project', '-p', help='直接进入指定项目')
def cli(server: str = None, project: str = None):
    """AxHost CLI - 交互式项目管理和文件同步工具"""
    
    async def run():
        shell = AxHostShell()
        
        # 如果指定了服务器地址
        if server:
            shell.config.server_url = server
            shell.api.set_base_url(server)
            shell.config.save()
        
        # 如果指定了项目，直接进入
        if project:
            from rich.progress import Progress
            with Progress(transient=True) as progress:
                task = progress.add_task("加载项目...", total=None)
                proj = await shell.project_service.get_project(project)
            
            if proj:
                shell.enter_session(proj)
            else:
                # 尝试搜索
                projects = await shell.project_service.search(project)
                if len(projects) == 1:
                    shell.enter_session(projects[0])
                elif projects:
                    console.print(f"找到多个匹配项目，请使用更精确的名称:")
                    for p in projects[:5]:
                        console.print(f"  - {p.name} ({p.object_id})")
                    return
                else:
                    console.print(f"[red]未找到项目: {project}[/red]")
                    return
        
        # 启动 Shell
        await shell.run()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        sys.exit(1)


def main():
    """主入口"""
    cli()


if __name__ == "__main__":
    main()
