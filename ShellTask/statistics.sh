#!/bin/bash

# 检查是否提供了目录参数
if [ $# -ne 1 ]; then
    echo "用法: $0 <目录路径>"
    exit 1
fi

# 检查目录是否存在
if [ ! -d "$1" ]; then
    echo "错误: '$1' 不是一个有效的目录"
    exit 1
fi

# 统计文件扩展名
echo "开始统计目录 '$1' 中的文件..."
echo "----------------------------------------"

# 使用find命令查找所有文件，然后提取扩展名并统计
find "$1" -type f | while read file; do
    # 获取文件名
    filename=$(basename "$file")
    
    # 提取扩展名（如果有的话）
    if [[ "$filename" == *.* ]]; then
        extension="${filename##*.}"
    else
        extension="无扩展名"
    fi
    
    # 转换为小写以便统一计数
    extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')
    
    echo "$extension"
done | sort | uniq -c | sort -nr | while read count ext; do
    printf "%-20s: %d 个文件\n" "$ext" "$count"
done

# 统计文件总数
total=$(find "$1" -type f | wc -l)
echo "----------------------------------------"
echo "文件总数: $total"
