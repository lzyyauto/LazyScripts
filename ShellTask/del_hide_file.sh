#!/bin/bash

# 检查是否提供了目录作为参数或请求帮助
if [ "$#" -eq 0 ]; then
    echo "用法: $0 <目录>"
    exit 1
fi

# 处理帮助选项
if [ "$1" == "-h" ]; then
    echo "用法: $0 <目录>"
    echo "此脚本用于删除指定目录及其子目录中所有以点开头的隐藏文件。"
    echo "例如: $0 /path/to/your/directory"
    exit 0
fi

# 检查是否提供了目录作为参数
if [ "$#" -ne 1 ]; then
    echo "用法: $0 <目录>"
    exit 1
fi

# 要处理的目录
DIRECTORY=$1

# 使用find命令查找所有以点开头的文件，并循环处理每个文件
find "$DIRECTORY" -type f -name '.*' -print0 | while IFS= read -r -d $'\0' file; do
    echo "正在删除: $file"
    rm "$file"
done
