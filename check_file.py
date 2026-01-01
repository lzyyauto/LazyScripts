#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse

def extract_name(filename, separator=' '):
    """
    从文件名中提取名称部分
    格式通常为 '字母-数字 分隔符 标题'，以指定的分隔符获取前面部分
    如果文件名中没有指定的分隔符，则返回整个文件名
    """
    if separator in filename:
        return filename.split(separator)[0]
    return filename

def compare_folders(folder_a, folder_b, quiet=False, separator=' '):
    """
    比较两个文件夹的内容
    只比较第一层目录，不递归搜索子目录
    """
    if not os.path.isdir(folder_a):
        print(f"错误: {folder_a} 不是一个有效的目录")
        return
    
    if not os.path.isdir(folder_b):
        print(f"错误: {folder_b} 不是一个有效的目录")
        return
    
    # 获取文件夹A中的所有项目
    items_a = os.listdir(folder_a)
    names_a = {extract_name(item, separator): item for item in items_a}
    
    # 获取文件夹B中的所有项目
    items_b = os.listdir(folder_b)
    names_b = {extract_name(item, separator): item for item in items_b}
    
    # 找出在A中但不在B中的项目
    only_in_a = set(names_a.keys()) - set(names_b.keys())
    
    # 找出在B中但不在A中的项目
    only_in_b = set(names_b.keys()) - set(names_a.keys())
    
    # 找出A和B中都有的项目
    common = set(names_a.keys()) & set(names_b.keys())
    
    # 输出结果
    print(f"\n文件夹A: {folder_a}")
    print(f"文件夹B: {folder_b}")
    print(f"\n总计: A中有{len(items_a)}个项目, B中有{len(items_b)}个项目")
    print(f"共同项目: {len(common)}个, 只在A中: {len(only_in_a)}个, 只在B中: {len(only_in_b)}个")
    
    # 如果是安静模式，不显示详细项目列表
    if quiet:
        return
    
    # 始终显示共同项目
    if common:
        print("\n在两个文件夹中都存在的项目:")
        for name in sorted(common):
            print(f"  {names_a[name]}")
    
    if only_in_a:
        print("\n只在文件夹A中存在的项目:")
        for name in sorted(only_in_a):
            print(f"  {names_a[name]}")
    
    if only_in_b:
        print("\n只在文件夹B中存在的项目:")
        for name in sorted(only_in_b):
            print(f"  {names_b[name]}")

def print_usage():
    print("\n使用方法: python3 check_file.py [文件夹A路径] [文件夹B路径] [选项]")
    print("\n选项:")
    print("  -q, --quiet     安静模式，只显示统计信息，不显示具体项目")
    print("  -s, --separator 指定文件名的分隔符，默认为空格")
    print("  -h, --help      显示此帮助信息并退出")
    print("\n说明:")
    print("  此脚本用于比较两个文件夹中的内容，只比较第一层目录，不递归搜索子目录。")
    print("  文件名格式通常为 '字母-数字 分隔符 标题'，脚本会以指定的分隔符获取前面部分进行比较。")
    print("  如果文件名中没有指定的分隔符，则使用整个文件名进行比较。")
    print("  默认分隔符为空格，可以通过 -s 或 --separator 选项指定其他分隔符。")
    sys.exit(0)

def main():
    if len(sys.argv) == 1 or '-h' in sys.argv or '--help' in sys.argv:
        print_usage()
    
    parser = argparse.ArgumentParser(description='比较两个文件夹中的内容，只比较第一层目录')
    parser.add_argument('folder_a', help='第一个文件夹路径')
    parser.add_argument('folder_b', help='第二个文件夹路径')
    parser.add_argument('-q', '--quiet', action='store_true', help='安静模式，只显示统计信息，不显示具体项目')
    parser.add_argument('-s', '--separator', default=' ', help='指定文件名的分隔符，默认为空格')
    
    args = parser.parse_args()
    compare_folders(args.folder_a, args.folder_b, args.quiet, args.separator)

if __name__ == '__main__':
    main()