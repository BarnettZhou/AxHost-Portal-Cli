"""AxHost API 客户端"""

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from ..models import Project, Tag, User


class APIError(Exception):
    """API 错误"""
    pass


class AuthenticationError(APIError):
    """认证错误"""
    pass


class AxHostClient:
    """AxHost API 客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def set_token(self, token: str) -> None:
        """设置认证令牌"""
        self._token = token
    
    def set_base_url(self, url: str) -> None:
        """设置基础 URL"""
        self.base_url = url.rstrip("/")
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers
    
    async def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Any:
        """发送 HTTP 请求"""
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        headers = self._get_headers()
        
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))
        
        try:
            response = await self._client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            )
            
            if response.status_code == 401:
                raise AuthenticationError("未登录或 Token 已过期")
            
            response.raise_for_status()
            
            if response.status_code == 204:
                return None
            
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.ConnectError as e:
            raise APIError(f"连接失败: {e}")
        except Exception as e:
            raise APIError(f"请求失败: {e}")
    
    async def get(self, path: str, params: Optional[Dict] = None) -> Any:
        """GET 请求"""
        return await self._request("GET", path, params=params)
    
    async def post(self, path: str, json: Optional[Dict] = None, **kwargs) -> Any:
        """POST 请求"""
        return await self._request("POST", path, json=json, **kwargs)
    
    async def put(self, path: str, json: Optional[Dict] = None) -> Any:
        """PUT 请求"""
        return await self._request("PUT", path, json=json)
    
    async def delete(self, path: str) -> Any:
        """DELETE 请求"""
        return await self._request("DELETE", path)
    
    async def check_server(self, url: Optional[str] = None) -> bool:
        """检查服务器是否可用"""
        try:
            check_url = url or self.base_url
            response = await self._client.get(f"{check_url}/api/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    # ========== 认证相关 ==========
    
    async def login(self, employee_id: str, password: str) -> Dict:
        """登录"""
        return await self.post("/api/auth/login", json={
            "employee_id": employee_id,
            "password": password
        })
    
    async def get_current_user(self) -> User:
        """获取当前用户"""
        data = await self.get("/api/auth/me")
        return User.from_dict(data)
    
    # ========== 项目相关 ==========
    
    async def list_projects(
        self,
        page: int = 1,
        per_page: int = 10,
        search: str = "",
        project_type: str = "my"
    ) -> Dict:
        """获取项目列表"""
        params = {
            "page": page,
            "per_page": per_page,
            "search": search,
            "project_type": project_type
        }
        return await self.get("/api/projects", params=params)
    
    async def get_project(self, project_id: str) -> Project:
        """获取项目详情"""
        data = await self.get(f"/api/projects/{project_id}")
        return Project.from_dict(data)
    
    async def create_project(self, project_data: Dict) -> Project:
        """创建项目"""
        data = await self.post("/api/projects", json=project_data)
        return Project.from_dict(data)
    
    async def update_project(self, project_id: str, project_data: Dict) -> Project:
        """更新项目"""
        data = await self.put(f"/api/projects/{project_id}", json=project_data)
        return Project.from_dict(data)
    
    async def delete_project(self, project_id: str) -> None:
        """删除项目"""
        await self.delete(f"/api/projects/{project_id}")
    
    async def upload_project_file(
        self,
        project_id: str,
        file_data: bytes,
        filename: str = "upload.zip"
    ) -> Dict:
        """上传项目文件"""
        url = f"{self.base_url}/api/projects/{project_id}/update-file"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        response = await self._client.post(
            url,
            headers=headers,
            files={"file": (filename, file_data, "application/zip")}
        )
        response.raise_for_status()
        return response.json()
    
    async def create_project_with_upload(
        self,
        file_data: bytes,
        name: str,
        **kwargs
    ) -> Project:
        """创建项目并上传文件"""
        url = f"{self.base_url}/api/projects/upload"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        
        data = {
            "name": name,
            "is_public": "true" if kwargs.get("is_public", True) else "false",
        }
        if kwargs.get("view_password"):
            data["view_password"] = kwargs["view_password"]
        if kwargs.get("remark"):
            data["remark"] = kwargs["remark"]
        if kwargs.get("tags"):
            import json
            data["tags"] = json.dumps(kwargs["tags"])
        
        response = await self._client.post(
            url,
            headers=headers,
            data=data,
            files={"file": ("upload.zip", file_data, "application/zip")}
        )
        response.raise_for_status()
        return Project.from_dict(response.json())
    
    # ========== 标签相关 ==========
    
    async def list_tags(self) -> List[Tag]:
        """获取标签列表"""
        data = await self.get("/api/tags")
        return [Tag.from_dict(t) for t in data.get("items", [])]
    
    async def create_tag(self, name: str, emoji: str = "📦") -> Tag:
        """创建标签"""
        data = await self.post("/api/tags", json={"name": name, "emoji": emoji})
        return Tag.from_dict(data)
    
    async def close(self) -> None:
        """关闭客户端"""
        await self._client.aclose()
