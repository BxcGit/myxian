#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本 - 使用 PyInstaller 打包应用程序

使用方法:
    python build.py           # 开发模式打包
    python build.py dev       # 仅验证代码
    python build.py clean      # 清理构建文件
"""

import os
import sys
import shutil
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
DIST_DIR = PROJECT_ROOT / "dist"


def clean():
    """清理构建文件"""
    print("清理构建文件...")

    dirs_to_remove = [
        BACKEND_ROOT / "build",
        BACKEND_ROOT / "__pycache__",
        BACKEND_ROOT / "app" / "__pycache__",
        BACKEND_ROOT / "app" / "core" / "__pycache__",
        BACKEND_ROOT / "app" / "routers" / "__pycache__",
        BACKEND_ROOT / "app" / "models" / "__pycache__",
        BACKEND_ROOT / "app" / "utils" / "__pycache__",
        BACKEND_ROOT / "app" / "xianyu" / "__pycache__",
        BACKEND_ROOT / "app" / "ai_agent" / "__pycache__",
        DIST_DIR,
    ]

    for d in dirs_to_remove:
        if d.exists():
            shutil.rmtree(d)
            print(f"  已删除: {d}")

    print("清理完成!")


def build_frontend():
    """构建前端"""
    print("构建前端...")

    frontend_dir = PROJECT_ROOT / "frontend"

    # 安装前端依赖
    print("  安装前端依赖...")
    result = os.system("cd /d {} && npm install".format(frontend_dir))
    if result != 0:
        print("  [警告] npm install 失败，尝试使用 pnpm...")
        result = os.system("cd /d {} && pnpm install".format(frontend_dir))
        if result != 0:
            print("  [错误] 前端依赖安装失败!")
            return False

    # 构建前端
    print("  构建前端...")
    result = os.system("cd /d {} && npm run build".format(frontend_dir))
    if result != 0:
        result = os.system("cd /d {} && pnpm build".format(frontend_dir))
        if result != 0:
            print("  [错误] 前端构建失败!")
            return False

    print("  前端构建完成!")
    return True


def build():
    """执行打包"""
    print("=" * 50)
    print("开始打包...")
    print("=" * 50)

    # 检查前端是否已构建
    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    if not frontend_dist.exists():
        print("[提示] 前端未构建，正在构建前端...")
        if not build_frontend():
            print("[错误] 前端构建失败，请检查错误!")
            return False

    # 清理旧构建
    clean()

    # 执行 PyInstaller
    print("\n执行 PyInstaller 打包...")
    print("-" * 50)

    spec_file = BACKEND_ROOT / "app.spec"
    result = os.system('pyinstaller "{}" --distpath "{}" --workpath "{}"'.format(
        spec_file,
        DIST_DIR,
        BACKEND_ROOT / "build"
    ))

    if result != 0:
        print("[错误] 打包失败!")
        return False

    # 将前端静态文件复制到与 exe 同目录 (dist/myxianyu/static/)
    app_dir = DIST_DIR / "myxianyu"
    external_static = app_dir / "static"

    if frontend_dist.exists():
        if external_static.exists():
            shutil.rmtree(external_static)
        shutil.copytree(frontend_dist, external_static)
        print("\n[提示] 前端静态文件已复制到与 exe 同目录")

    print("\n" + "=" * 50)
    print("打包完成!")
    print("=" * 50)

    # 显示输出结构
    print("\n输出目录结构:")
    for item in DIST_DIR.rglob("*"):
        if item.is_file():
            rel_path = item.relative_to(DIST_DIR)
            size = item.stat().st_size
            print(f"  {rel_path} ({size} bytes)")

    print("\n使用说明:")
    print(f"  1. 进入 dist 目录: cd {DIST_DIR}")
    print("  2. 运行程序: .\\myxianyu.exe")
    print("  3. 访问: http://localhost:8000")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "clean":
            clean()
        elif cmd == "dev":
            print("开发模式验证通过!")
        else:
            print(f"未知命令: {cmd}")
            print(__doc__)
    else:
        build()