.PHONY: help venv install install-dev run test lint format clean

help:
	@echo "AxHost CLI - 可用命令:"
	@echo "  make venv        - 创建 uv 虚拟环境"
	@echo "  make install     - 安装生产依赖"
	@echo "  make install-dev - 安装开发依赖"
	@echo "  make run         - 运行 CLI"
	@echo "  make test        - 运行测试"
	@echo "  make lint        - 代码检查"
	@echo "  make format      - 代码格式化"
	@echo "  make clean       - 清理缓存文件"

venv:
	uv venv

install:
	uv pip install -e "."

install-dev:
	uv pip install -e ".[dev]"

run:
	uv run python -m axhost_cli

test:
	uv run pytest -v

lint:
	uv run ruff check axhost_cli/
	uv run mypy axhost_cli/

format:
	uv run black axhost_cli/
	uv run ruff check --fix axhost_cli/

clean:
	rm -rf .venv __pycache__ .pytest_cache *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
