"""项目服务"""

from typing import List, Optional

from ..api.client import AxHostClient
from ..config import Config
from ..models import Project, ProjectCreateData


class ProjectService:
    """项目服务"""
    
    def __init__(self, api: AxHostClient, config: Config):
        self.api = api
        self.config = config
        self._projects: List[Project] = []
        self._current_project: Optional[Project] = None
    
    async def list_projects(
        self,
        search: str = "",
        page: int = 1,
        per_page: int = 10,
        project_type: str = "my"
    ) -> List[Project]:
        """获取项目列表"""
        data = await self.api.list_projects(
            page=page,
            per_page=per_page,
            search=search,
            project_type=project_type
        )
        self._projects = [Project.from_dict(p) for p in data.get("items", [])]
        return self._projects
    
    async def search(self, query: str) -> List[Project]:
        """搜索项目"""
        return await self.list_projects(search=query)
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """获取项目详情"""
        try:
            return await self.api.get_project(project_id)
        except Exception:
            return None
    
    async def create_project(
        self,
        name: str,
        remark: str = "",
        is_public: bool = True,
        view_password: Optional[str] = None,
        tag_names: Optional[List[str]] = None
    ) -> Project:
        """创建项目（仅元数据）"""
        data = {
            "name": name,
            "remark": remark,
            "is_public": is_public,
            "tag_names": tag_names or []
        }
        if view_password:
            data["view_password"] = view_password
        
        return await self.api.create_project(data)
    
    async def create_project_with_upload(
        self,
        file_data: bytes,
        name: str,
        remark: str = "",
        is_public: bool = True,
        view_password: Optional[str] = None,
        tag_names: Optional[List[str]] = None
    ) -> Project:
        """创建项目并上传文件"""
        return await self.api.create_project_with_upload(
            file_data=file_data,
            name=name,
            remark=remark,
            is_public=is_public,
            view_password=view_password,
            tags=tag_names or []
        )
    
    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        remark: Optional[str] = None,
        is_public: Optional[bool] = None,
        view_password: Optional[str] = None,
        tag_names: Optional[List[str]] = None
    ) -> Project:
        """更新项目"""
        data = {}
        if name is not None:
            data["name"] = name
        if remark is not None:
            data["remark"] = remark
        if is_public is not None:
            data["is_public"] = is_public
        if view_password is not None:
            data["view_password"] = view_password
        if tag_names is not None:
            data["tag_names"] = tag_names
        
        return await self.api.update_project(project_id, data)
    
    async def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        try:
            await self.api.delete_project(project_id)
            return True
        except Exception:
            return False
    
    def get_current(self) -> Optional[Project]:
        """获取当前项目"""
        return self._current_project
    
    def set_current(self, project: Optional[Project]) -> None:
        """设置当前项目"""
        self._current_project = project
        if project:
            self.config.current_project = project.object_id
        else:
            self.config.current_project = None
        self.config.save()
    
    async def load_current_project(self) -> Optional[Project]:
        """加载当前项目"""
        if self.config.current_project:
            project = await self.get_project(self.config.current_project)
            if project:
                self._current_project = project
                return project
        return None
