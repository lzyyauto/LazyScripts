#!/bin/bash

# 源文件夹路径
source_folder="/mnt/user/Downloads/03.black/Hamasaki Mao part 3"
# 目标文件夹路径
destination_folder="/mnt/user/Machine learning/滨崎真绪Hamasaki Mao"

# 检查目标文件夹是否存在，不存在则创建
if [ ! -d "$destination_folder" ]; then
    mkdir -p "$destination_folder"
fi

# 遍历源文件夹中的所有文件
for file in "$source_folder"/*; do
    # 获取文件名（不包括扩展名）
    filename=$(basename "$file")
    base_name="${filename%.*}"
    
    # 创建以文件名命名的文件夹
    target_folder="$destination_folder/$base_name"
    if [ ! -d "$target_folder" ]; then
        mkdir -p "$target_folder"
    fi
    
    # 将文件移动到对应的目标文件夹
    mv "$file" "$target_folder/"
done

echo "文件整理完成！"
