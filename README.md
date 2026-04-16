# AxHost CLI

AxHost CLI 是一个面向开发者和产品经理的**交互式 Shell**工具，用于项目管理和文件同步。采用**双模式架构**：
- **全局模式**: 浏览、搜索、创建项目
- **Session 模式**: 针对特定项目的操作（关联目录、同步、管理等）

## 特性

- 🚀 **极速启动** - <500ms 启动时间
- 🎯 **双模式架构** - 全局浏览 + Session 专注
- 🔍 **智能搜索** - 实时过滤、Tab 补全
- 📖 **交互式列表** - 翻页、搜索、选择一体化
- 🔐 **浏览器登录** - OAuth 安全认证
- 📦 **一键同步** - 自动打包，实时进度
- 📦 **批量同步** - 批量检测并同步多个项目

## 安装

### 使用 uv（推荐）

```bash
# 创建虚拟环境
uv venv

# 安装依赖
uv pip install -e "."

# 或同步 lock 文件（如果有）
uv pip sync requirements.txt
```

### 使用 pip

```bash
pip install -e "."
```

## 快速开始

```bash
# 启动 CLI
axhost

# 配置服务器
axhost> /host http://localhost:8000

# 登录
axhost> /login

# 浏览项目
axhost> /projects

# 创建项目
axhost> /create

# 进入项目 Session
axhost> /use my-project

# 关联目录并同步
[my-project]> /link ./dist
[my-project]> /sync

# 批量同步所有项目
axhost> /sync-all
```

## 命令速查

### 全局命令

| 命令 | 功能 |
|------|------|
| `/host <url>` | 设置服务器地址 |
| `/login` | 浏览器自动登录（`--password` / `-p` 账号密码登录） |
| `/logout` | 退出登录 |
| `/use [name]` | 搜索/浏览并进入项目 Session |
| `/create` | 交互式创建新项目 |
| `/projects` | 交互式项目列表 |
| `/sync-all` | 批量同步有更新的项目 |
| `/help` | 查看帮助 |
| `/exit` | 退出 CLI |

### Session 命令

| 命令 | 功能 |
|------|------|
| `/link <path>` | 关联本地目录 |
| `/sync` | 同步文件到线上 |
| `/rename <name>` | 重命名项目 |
| `/edit` | 交互式编辑项目 |
| `/info` | 查看项目详情 |
| `/view` | 浏览器打开预览 |
| `/delete` | 删除项目（需确认） |
| `/exit` | 返回全局模式 |

## 开发

```bash
# 创建虚拟环境
uv venv

# 安装开发依赖（使用 uv）
uv pip install -e ".[dev]"

# 或安装生产依赖
uv pip install -e "."

# 运行测试
pytest

# 代码格式化
black axhost_cli/
ruff check axhost_cli/
```

## 使用 uv 的常用命令

```bash
# 创建虚拟环境
uv venv

# 安装所有依赖（包括开发依赖）
uv pip install -e ".[dev]"

# 仅安装生产依赖
uv pip install -e "."

# 从 requirements.txt 安装
uv pip install -r requirements.txt

# 生成 lock 文件
uv pip compile pyproject.toml -o requirements.lock

# 同步依赖（根据 lock 文件）
uv pip sync requirements.lock

# 运行 CLI
uv run axhost
# 或
python -m axhost_cli
```

## 相关项目

- [AxHost](https://github.com/BarnettZhou/AxHost) - FastAPI 服务端
- [AxHost-Portal](https://github.com/BarnettZhou/AxHost-Portal) - Electron 桌面端

## License

MIT
