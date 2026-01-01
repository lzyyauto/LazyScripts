#!/bin/bash

# 设置文件所在的目录
directory="/mnt/user/Anime/全职猎人 (1999)/Season 1"

# 切换到指定目录
cd "$directory"

# 遍历目录中的所有.mkv文件
for file in *.mkv; do
    # 使用正则表达式提取集数
    if [[ "$file" =~ TV([0-9]+) ]]; then
        episode_number=${BASH_REMATCH[1]}
        # 格式化新文件名
        new_filename="全职猎人.S01E$(printf "%02d" "$episode_number").mkv"
        # 重命名文件
        mv "$file" "$new_filename"
        echo "已将 \"$file\" 重命名为 \"$new_filename\""
    fi
done
