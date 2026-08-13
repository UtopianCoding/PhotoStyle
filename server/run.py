"""
PhotoStyle 后端启动脚本

用法：
    # 方式1：直接运行本脚本（推荐，自动读取 .env 中的 APP_HOST / APP_PORT）
    python run.py

    # 方式2：开发模式（热重载，保存代码自动重启）
    python run.py --reload

    # 方式3：直接使用 uvicorn 命令
    venv\\Scripts\\uvicorn.exe app.main:app --host 0.0.0.0 --port 7823 --reload
"""

from __future__ import annotations

import argparse
import sys

from app.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="PhotoStyle 后端启动脚本")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载（开发模式，保存代码自动重启）",
    )
    parser.add_argument(
        "--host",
        default=None,
        help=f"监听地址，默认读取 APP_HOST={settings.app.host}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"监听端口，默认读取 APP_PORT={settings.app.port}",
    )
    args = parser.parse_args()

    host = args.host or settings.app.host
    port = args.port or settings.app.port

    try:
        import uvicorn
    except ImportError as exc:
        print(f"[ERROR] 未安装 uvicorn: {exc}")
        print("请先安装依赖：venv\\Scripts\\pip.exe install -r requirements.txt")
        sys.exit(1)

    print(f"[启动] PhotoStyle 后端服务")
    print(f"  Host:   {host}")
    print(f"  Port:   {port}")
    print(f"  Reload: {'ON' if args.reload else 'OFF'}")
    print(f"  Env:    {settings.app.env}")
    print(f"  Docs:   http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")
    print("-" * 50)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
