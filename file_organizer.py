#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件整理脚本：将指定目录下的文件按扩展名分类并移动到相应文件夹中

用法：
  python file_organizer.py [目录路径]
  python file_organizer.py -h           # 显示帮助信息
  python file_organizer.py --help       # 显示帮助信息
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def organize_files_by_extension(directory):
    """
    将指定目录下的文件按扩展名分类并移动到相应文件夹中
    
    参数:
        directory (str): 目标目录的路径
    """
    # 确保目录存在
    if not os.path.isdir(directory):
        print(f"错误: {directory} 不是有效的目录路径")
        return False

    # 获取目录下的所有文件（仅第一层，不包括子目录中的文件）
    files = [
        f for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    # 处理每个文件
    for file in files:
        # 跳过脚本自身
        if file == os.path.basename(__file__):
            continue

        file_path = os.path.join(directory, file)

        # 获取文件扩展名（不带点，统一为大写）
        ext = os.path.splitext(file)[1].lstrip('.').upper()

        # 如果没有扩展名，使用"NO_EXT"作为文件夹名
        if not ext:
            ext = "NO_EXT"

        # 创建目标文件夹
        target_dir = os.path.join(directory, ext)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # 移动文件
        target_path = os.path.join(target_dir, file)

        try:
            shutil.move(file_path, target_path)
            print(f"已移动: {file} -> {ext}/{file}")
        except Exception as e:
            print(f"移动 {file} 时出错: {str(e)}")

    return True


def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(
        description='文件整理工具：将指定目录下的文件按扩展名分类并移动到相应文件夹中',
        epilog='''
示例:
  python file_organizer.py                    # 整理当前目录
  python file_organizer.py /path/to/folder   # 整理指定目录
  python file_organizer.py ~/Downloads       # 整理下载文件夹

说明:
  - 只处理目标目录下的一层文件，不递归遍历子目录
  - 扩展名不区分大小写（.jpg和.JPG都归类到JPG文件夹）
  - 没有扩展名的文件会放到NO_EXT文件夹中
  - 会自动创建以扩展名大写命名的文件夹
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('directory',
                        nargs='?',
                        default=os.getcwd(),
                        help='要整理的目录路径（默认为当前目录）')

    # 解析命令行参数
    args = parser.parse_args()
    directory = args.directory

    # 如果使用了默认目录，提示用户
    if directory == os.getcwd() and len(sys.argv) == 1:
        print(f"未提供目录路径，将使用当前目录: {directory}")

    # 组织文件
    print(f"开始整理目录: {directory}")
    if organize_files_by_extension(directory):
        print("文件整理完成！")
    else:
        print("文件整理失败！")


if __name__ == "__main__":
    main()
