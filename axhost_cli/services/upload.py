"""上传服务"""

import os
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn

from ..api.client import AxHostClient
from ..models import UploadResult


class UploadService:
    """上传服务"""
    
    # 默认排除的文件和目录
    DEFAULT_EXCLUDE = {
        '.git', '.gitignore', '.svn', '.hg',
        'node_modules', '__pycache__', '.pytest_cache',
        '.DS_Store', 'Thumbs.db', '.idea', '.vscode',
        '*.pyc', '*.pyo', '*.pyd', '.Python',
        '*.so', '*.dylib', '*.dll',
        '*.log', '*.tmp', '*.temp',
        '.env', '.env.local', '.env.*.local',
    }
    
    def __init__(self, api: AxHostClient):
        self.api = api
        self.console = Console()
    
    async def sync(
        self,
        dir_path: str,
        project_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> UploadResult:
        """同步目录到项目"""
        path = Path(dir_path)
        
        if not path.exists():
            return UploadResult(success=False, error_message=f"路径不存在: {path}")
        
        if not path.is_dir():
            return UploadResult(success=False, error_message=f"不是目录: {path}")
        
        try:
            # 1. 打包目录
            with self.console.status("[bold green]正在打包目录..."):
                zip_path, file_count, size_bytes = await self._pack_directory(path)
            
            self.console.print(f"   发现 {file_count} 个文件, {self._format_size(size_bytes)}")
            
            # 2. 上传
            result = await self._upload_zip(
                zip_path,
                project_id,
                progress_callback
            )
            
            # 3. 清理临时文件
            zip_path.unlink(missing_ok=True)
            
            return result
            
        except Exception as e:
            return UploadResult(success=False, error_message=str(e))
    
    async def _pack_directory(self, dir_path: Path) -> tuple[Path, int, int]:
        """打包目录为 zip"""
        temp_dir = Path(tempfile.gettempdir()) / "axhost"
        temp_dir.mkdir(exist_ok=True)
        
        zip_path = temp_dir / f"{dir_path.name}-{int(time.time())}.zip"
        
        file_count = 0
        total_size = 0
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in dir_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                if self._should_exclude(file_path, dir_path):
                    continue
                
                arcname = file_path.relative_to(dir_path)
                zf.write(file_path, arcname)
                
                file_count += 1
                total_size += file_path.stat().st_size
        
        return zip_path, file_count, total_size
    
    def _should_exclude(self, file_path: Path, base_path: Path) -> bool:
        """检查是否应该排除"""
        # 检查文件扩展名
        if file_path.suffix in {'.pyc', '.pyo', '.tmp', '.temp', '.log'}:
            return True
        
        # 检查路径中的目录名
        parts = file_path.relative_to(base_path).parts
        for part in parts:
            if part in self.DEFAULT_EXCLUDE:
                return True
            # 检查隐藏文件（以点开头的文件）
            if part.startswith('.') and part not in {'.', '..'}:
                # 保留 .htaccess 等可能有用的隐藏文件
                if part not in {'.htaccess', '.well-known'}:
                    return True
        
        return False
    
    async def _upload_zip(
        self,
        zip_path: Path,
        project_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> UploadResult:
        """上传 zip 文件"""
        file_size = zip_path.stat().st_size
        
        # 读取文件内容
        file_data = zip_path.read_bytes()
        
        try:
            # 使用进度条
            with Progress(
                TextColumn("上传中..."),
                BarColumn(bar_width=30),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("upload", total=file_size)
                
                # 上传（httpx 会自动处理进度）
                result = await self.api.upload_project_file(
                    project_id=project_id,
                    file_data=file_data,
                    filename=zip_path.name
                )
                
                progress.update(task, completed=file_size)
            
            url = f"{self.api.base_url}/projects/{project_id}/"
            return UploadResult(
                success=True,
                url=url,
                file_count=len(file_data),
                size_bytes=file_size
            )
            
        except Exception as e:
            return UploadResult(success=False, error_message=str(e))
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def get_preview_url(self, project_id: str, entry_file: str = "") -> str:
        """获取预览 URL"""
        base_url = f"{self.api.base_url}/projects/{project_id}/"
        if entry_file:
            base_url += entry_file
        return base_url
