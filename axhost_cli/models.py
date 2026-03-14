"""数据模型定义"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    PRODUCT_MANAGER = "product_manager"
    DEVELOPER = "developer"


class UserStatus(str, Enum):
    """用户状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class User:
    """用户模型"""
    id: int
    name: str
    employee_id: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            name=data["name"],
            employee_id=data["employee_id"],
            role=UserRole(data.get("role", "developer")),
            status=UserStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )


@dataclass
class Tag:
    """标签模型"""
    id: int
    name: str
    emoji: str = "📦"
    
    @classmethod
    def from_dict(cls, data: dict) -> "Tag":
        return cls(
            id=data["id"],
            name=data["name"],
            emoji=data.get("emoji", "📦"),
        )


@dataclass
class Project:
    """项目模型"""
    object_id: str
    name: str
    author_name: str
    author_id: int
    created_at: datetime
    updated_at: datetime
    is_public: bool = False
    view_password: Optional[str] = None
    remark: str = ""
    tags: List[Tag] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            object_id=data["object_id"],
            name=data["name"],
            author_name=data.get("author_name", "未知"),
            author_id=data.get("author_id", 0),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            is_public=data.get("is_public", False),
            view_password=data.get("view_password"),
            remark=data.get("remark", ""),
            tags=[Tag.from_dict(t) for t in data.get("tags", [])],
        )


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[User] = None
    error_message: Optional[str] = None
    should_retry: bool = False


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    url: Optional[str] = None
    file_count: int = 0
    size_bytes: int = 0
    error_message: Optional[str] = None


@dataclass
class BatchSyncResult:
    """批量同步结果"""
    project_id: str
    project_name: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class ProjectCreateData:
    """项目创建数据"""
    name: str
    remark: str = ""
    is_public: bool = True
    view_password: Optional[str] = None
    tag_names: List[str] = field(default_factory=list)
