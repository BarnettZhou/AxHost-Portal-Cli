# AxHost CLI - Agent 开发指南

## 项目概述

AxHost CLI 是一个面向开发者和产品经理的**交互式 Shell**工具，采用**双模式架构**：
- **全局模式**: 浏览、搜索、创建项目
- **Session 模式**: 针对特定项目的操作（关联目录、同步、管理等）

## 项目结构

```
axhost_cli/              # 主包目录
├── __init__.py          # 版本信息
├── __main__.py          # 入口点
├── main.py              # CLI 主程序
├── shell.py             # 交互式 Shell 核心
├── models.py            # 数据模型
├── config.py            # 配置管理
├── completer.py         # 自动补全
├── api/
│   ├── __init__.py
│   └── client.py        # HTTP API 客户端
├── services/
│   ├── __init__.py
│   ├── auth.py          # 认证服务
│   ├── project.py       # 项目服务
│   ├── upload.py        # 上传服务
│   └── batch_sync.py    # 批量同步服务
└── ui/
    ├── __init__.py
    ├── interactive.py   # 交互式列表组件
    └── widgets.py       # UI 组件
```

## 技术栈

- **交互层**: `prompt_toolkit` + `Rich`
- **HTTP 客户端**: `httpx` (异步)
- **配置管理**: `pydantic` + `keyring`
- **打包**: `zipfile` (标准库)

## 双模式架构

### 全局模式 (Global Mode)
- 默认状态，未进入任何项目
- 可浏览所有项目、创建新项目
- 提示符: `axhost>`

### Session 模式
- 已进入特定项目，所有操作针对该项目
- 可关联目录、同步文件、管理项目
- 提示符: `[项目名称]>`

### 模式流转
```
全局模式 ──/use, /create, /projects──► Session 模式
   ▲                                    │
   └── /exit, /use 其他项目 ────────────┘
```

## 命令分类

### 全局命令
- `/host <url>` - 设置服务器地址
- `/login` - 浏览器自动登录
- `/login --password` 或 `/login -p` - 使用账号密码登录（交互式输入）
- `/use [name]` - 搜索并进入项目 Session
- `/create` - 交互式创建新项目
- `/projects` - 交互式项目列表
- `/sync-all` - 批量同步有更新的项目
- `/help` - 查看帮助
- `/exit` - 退出 CLI

### Session 命令
- `/link <path>` - 关联本地目录
- `/sync` - 同步文件到线上
- `/rename <new_name>` - 重命名项目
- `/edit` - 交互式编辑项目
- `/info` - 查看项目详情
- `/view` - 浏览器打开预览
- `/delete` - 删除项目（需确认）
- `/exit` - 返回全局模式

## 代码规范

1. **类型注解**: 所有函数和类都必须使用类型注解
2. **异步**: 所有 IO 操作都使用 async/await
3. **错误处理**: 使用异常而非返回错误码
4. **配置**: 使用 Pydantic 模型管理配置
5. **API 响应**: 使用 dataclass 定义响应模型

## 环境配置

开发环境需要 Python 3.9+，依赖管理使用 uv（推荐）或 pip：

### 使用 uv（推荐）

```bash
# 创建虚拟环境
uv venv

# 安装依赖（开发模式）
uv pip install -e ".[dev]"

# 或从 requirements.txt 安装
uv pip install -r requirements.txt

# 运行 CLI
python -m axhost_cli
```

### 使用 pip

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -e ".[dev]"

# 运行 CLI
python -m axhost_cli
```

## 调试技巧

1. 使用 `AXHOST_DEBUG=1` 开启调试模式
2. 日志输出到 `~/.axhost/logs/cli.log`
3. 配置存储在 `~/.axhost/config.json`
4. Token 存储在系统密钥环中
