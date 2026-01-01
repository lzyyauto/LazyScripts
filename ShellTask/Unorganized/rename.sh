#!/bin/bash

# 当前脚本目录作为工作目录
work_dir="$(pwd)"

# 排除的目录
exclude_dir="./Pic"

# 结果输出文件
results="${work_dir}/renamed_items.txt"
> "$results" # 清空之前的内容

# 输出开始信息
echo "Starting renaming process..." | tee -a "$results"

# 遍历除了./Pic外的所有文件和文件夹
find "$work_dir" -type d -path "$exclude_dir" -prune -o -type d -o -type f -print | while IFS= read -r item; do
    # 获取项的基本名称和目录路径
    base_name=$(basename "$item")
    dir_path=$(dirname "$item")

    # 忽略根目录
    if [[ "$item" == "$work_dir" ]]; then
        continue
    fi

    # 检测和转换规则：将符合{字母}-{数字}或{字母A}-{数字}-{字母B}的名称转为大写
    new_name=$(echo "$base_name" | sed -r 's/([a-zA-Z]+)-([0-9]+)(-([a-zA-Z]+))?/\U&/')

    # 如果名称有变化，则进行重命名并记录
    if [[ "$new_name" != "$base_name" ]]; then
        mv "$item" "$dir_path/$new_name"
        echo "Renamed: $base_name to $new_name" | tee -a "$results"
    fi
done

# 输出结束信息
echo "Renaming completed. Processed items are listed in $results" | tee -a "$results"
