"""命令补全"""

from typing import Iterable, List

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class CommandCompleter(Completer):
    """命令补全器 - 支持 TAB 补全命令"""
    
    # 全局命令: (名称, 描述)
    GLOBAL_COMMANDS = [
        ("host", "设置或查看服务器地址"),
        ("login", "浏览器自动登录 或 /login --password/-p 账号密码登录"),
        ("logout", "退出登录"),
        ("use", "搜索并进入项目 Session"),
        ("create", "交互式创建新项目"),
        ("projects", "交互式浏览项目列表"),
        ("sync-all", "批量同步有更新的项目"),
        ("help", "查看帮助信息"),
        ("exit", "退出当前 Session，返回全局模式"),
        ("bye", "退出 AxHost CLI"),
    ]
    
    # Session 命令
    SESSION_COMMANDS = [
        ("link", "关联本地目录"),
        ("sync", "同步文件到线上"),
        ("rename", "重命名项目"),
        ("edit", "交互式编辑项目"),
        ("info", "查看项目详情"),
        ("view", "浏览器打开预览"),
        ("delete", "删除项目"),
        ("exit", "退出当前 Session，返回全局模式"),
        ("bye", "退出 AxHost CLI"),
    ]
    
    def __init__(self, shell=None):
        self.shell = shell
    
    def get_completions(
        self,
        document: Document,
        complete_event
    ) -> Iterable[Completion]:
        """获取补全建议 - 只补全命令，不补全参数"""
        text = document.text.lstrip()
        
        # 确定当前模式
        is_session = self.shell and hasattr(self.shell, 'mode') and self.shell.mode.value == "session" if self.shell else False
        
        # 获取可用命令列表
        available_commands = list(self.GLOBAL_COMMANDS)
        if is_session:
            available_commands.extend(self.SESSION_COMMANDS)
        
        # 如果包含空格，说明在输入参数，不提供补全（避免卡顿）
        if ' ' in text:
            return
        
        # 输入以 / 开头：命令补全
        if text.startswith('/'):
            cmd_part = text[1:]  # 去掉开头的 /
            
            for name, desc in available_commands:
                if name.startswith(cmd_part.lower()):
                    yield Completion(
                        f"/{name}",
                        start_position=-len(text),
                        display=f"/{name}",
                        display_meta=desc
                    )
        
        # 输入为空：显示所有命令
        elif not text:
            for name, desc in available_commands:
                yield Completion(
                    f"/{name}",
                    start_position=0,
                    display=f"/{name}",
                    display_meta=desc
                )
