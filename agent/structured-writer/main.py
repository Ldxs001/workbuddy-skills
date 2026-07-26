#!/usr/bin/env python3
"""Structured Writer — 结构化写作智能体 入口"""
import sys
import argparse
from structured_writer.web_ui import run_server


def main():
    parser = argparse.ArgumentParser(
        description="Structured Writer — 结构化写作智能体"
    )
    parser.add_argument("--port", type=int, default=8770,
                        help="Web UI 端口（默认 8770）")
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="监听地址（默认 0.0.0.0）")
    args = parser.parse_args()

    print("=" * 50)
    print("  Structured Writer · 结构化写作智能体")
    print(f"  版本: {get_version()}")
    print("=" * 50)
    print()

    run_server(host=args.host, port=args.port)


def get_version():
    try:
        from structured_writer import __version__
        return __version__
    except ImportError:
        return "dev"


if __name__ == "__main__":
    main()
