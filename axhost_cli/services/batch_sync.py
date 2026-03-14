"""批量同步服务"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

from ..api.client import AxHostClient
from ..config import Config
from ..models import BatchSyncResult, Project
from .project import ProjectService
from .upload import UploadService


class BatchSyncService:
    """批量同步服务"""
    
    def __init__(
        self,
        api: AxHostClient,
        config: Config,
        project_service: ProjectService
    ):
        self.api = api
        self.config = config
        self.project_service = project_service
        self.upload_service = UploadService(api)
        self.console = Console()
    
    async def scan_pending_syncs(self) -> List[Tuple[Project, str, datetime]]:
        """
        扫描需要同步的项目
        
        返回: [(project, dir_path, local_mtime), ...]
        """
        pending = []
        
        for project_id, dir_path in self.config.linked_dirs.items():
            path = Path(dir_path)
            if not path.exists() or not path.is_dir():
                continue
            
            # 获取本地目录最后修改时间
            local_mtime = self._get_dir_mtime(path)
            if not local_mtime:
                continue
            
            # 获取上次同步时间
            last_sync = self.config.get_last_sync(project_id)
            
            # 如果本地修改时间 > 上次同步时间，需要更新
            if not last_sync or local_mtime > last_sync:
                # 获取项目信息
                project = await self.project_service.get_project(project_id)
                if project:
                    pending.append((project, str(path), local_mtime))
        
        # 按本地修改时间排序（旧的在前）
        pending.sort(key=lambda x: x[2])
        
        return pending
    
    def _get_dir_mtime(self, dir_path: Path) -> Optional[datetime]:
        """获取目录的最后修改时间（所有文件中最大的 mtime）"""
        max_mtime = 0.0
        
        try:
            for root, dirs, files in os.walk(dir_path):
                # 跳过排除的目录
                dirs[:] = [d for d in dirs if d not in UploadService.DEFAULT_EXCLUDE]
                
                for file in files:
                    file_path = Path(root) / file
                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime > max_mtime:
                            max_mtime = mtime
                    except (OSError, IOError):
                        continue
        except Exception:
            return None
        
        if max_mtime > 0:
            return datetime.fromtimestamp(max_mtime)
        return None
    
    def format_pending_list(
        self,
        pending: List[Tuple[Project, str, datetime]]
    ) -> Table:
        """格式化待同步列表"""
        table = Table(show_header=True, header_style="bold")
        table.add_column("序号", width=5)
        table.add_column("项目名称", width=25)
        table.add_column("关联目录", width=25)
        table.add_column("最后更新", width=20)
        
        for i, (project, dir_path, mtime) in enumerate(pending, 1):
            table.add_row(
                str(i),
                project.name[:24],
                dir_path[:24],
                mtime.strftime("%Y-%m-%d %H:%M:%S")
            )
        
        return table
    
    async def batch_sync(
        self,
        pending: List[Tuple[Project, str, datetime]]
    ) -> List[BatchSyncResult]:
        """批量同步项目"""
        results = []
        total = len(pending)
        
        for i, (project, dir_path, mtime) in enumerate(pending, 1):
            self.console.print()
            self.console.print(f"[bold]{'─' * 60}")
            self.console.print(f"[{i}/{total}] 开始更新: [bold cyan]{project.name}[/bold cyan]")
            
            try:
                # 执行同步
                result = await self.upload_service.sync(dir_path, project.object_id)
                
                if result.success:
                    # 更新同步时间
                    self.config.set_last_sync(project.object_id)
                    self.config.save()
                    
                    self.console.print(f"[green]✓[/green] 同步完成")
                    if result.url:
                        self.console.print(f"   URL: {result.url}")
                    
                    results.append(BatchSyncResult(
                        project_id=project.object_id,
                        project_name=project.name,
                        success=True
                    ))
                else:
                    self.console.print(f"[red]✗[/red] 同步失败: {result.error_message}")
                    results.append(BatchSyncResult(
                        project_id=project.object_id,
                        project_name=project.name,
                        success=False,
                        error_message=result.error_message
                    ))
                    
            except Exception as e:
                self.console.print(f"[red]✗[/red] 同步失败: {e}")
                results.append(BatchSyncResult(
                    project_id=project.object_id,
                    project_name=project.name,
                    success=False,
                    error_message=str(e)
                ))
        
        return results
    
    def get_linked_count(self) -> int:
        """获取关联项目数量"""
        return len(self.config.linked_dirs)
