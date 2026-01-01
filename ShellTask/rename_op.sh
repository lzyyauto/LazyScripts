#!/bin/bash

# 检查参数数量
if [ $# -lt 1 ]; then
    echo "用法: $0 <目录路径>"
    exit 1
fi

directory="$1"

# 确保目录存在
if [ ! -d "$directory" ]; then
    echo "错误: 目录 '$directory' 不存在"
    exit 1
fi

# 从路径中提取季数
season_number=$(echo "$directory" | grep -oP 'Season \K\d+')

if [ -z "$season_number" ]; then
    echo "错误: 无法从路径中提取季数。路径必须包含 'Season X' 或 'Season XX'"
    exit 1
fi

# 格式化季数(补零)
season_formatted=$(printf "S%02d" $season_number)

# 遍历目录中的所有mkv文件
find "$directory" -type f -name "*.mkv" | while read -r file; do
    filename=$(basename "$file")
    
    # 提取剧名（第一个数字之前的所有内容）
    series_name=$(echo "$filename" | grep -oP '^[^0-9]+' | sed 's/[[:space:]]*$//')
    
    # 提取集数（第一组4位数字）
    episode_number=$(echo "$filename" | grep -oP '\d{4}' | head -1 | sed 's/^0*//')
    episode_formatted=$(printf "E%02d" $episode_number)
    
    # 提取剧集标题（第一个数字之后到第一个点之前的内容）
    episode_title=$(echo "$filename" | sed -E 's/^[^0-9]*[0-9]{4}//' | sed -E 's/\.1080p.*$//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    
    # 构建新文件名
    new_filename="${series_name} - ${season_formatted}${episode_formatted} - ${episode_title}.mkv"
    
    # 执行重命名
    mv "$file" "$(dirname "$file")/$new_filename"
    echo "已重命名: $filename -> $new_filename"
done
