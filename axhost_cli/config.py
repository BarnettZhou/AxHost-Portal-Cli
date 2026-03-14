"""配置管理"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field


DEFAULT_SERVER_URL = "http://localhost:8000"
CONFIG_DIR = Path.home() / ".axhost"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config(BaseModel):
    """配置模型"""
    
    server_url: str = DEFAULT_SERVER_URL
    current_project: Optional[str] = None
    linked_dirs: Dict[str, str] = Field(default_factory=dict)
    last_sync: Dict[str, str] = Field(default_factory=dict)
    
    @classmethod
    def load(cls) -> "Config":
        """从文件加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**data)
            except Exception:
                pass
        return cls()
    
    def save(self) -> None:
        """保存配置到文件"""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
    
    def get_linked_dir(self, project_id: str) -> Optional[str]:
        """获取项目的关联目录"""
        return self.linked_dirs.get(project_id)
    
    def set_linked_dir(self, project_id: str, path: str) -> None:
        """设置项目的关联目录"""
        self.linked_dirs[project_id] = path
    
    def get_last_sync(self, project_id: str) -> Optional[datetime]:
        """获取项目的最后同步时间"""
        time_str = self.last_sync.get(project_id)
        if time_str:
            try:
                return datetime.fromisoformat(time_str)
            except ValueError:
                pass
        return None
    
    def set_last_sync(self, project_id: str, time: Optional[datetime] = None) -> None:
        """设置项目的最后同步时间"""
        if time is None:
            time = datetime.now()
        self.last_sync[project_id] = time.isoformat()
