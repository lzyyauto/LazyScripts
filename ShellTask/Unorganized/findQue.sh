#!/bin/bash

# 指定处理目录
DIR="/mnt/user/Repository/ACG/comic/One Piece Color"

# 输出文件
OUTPUT="op.txt"

# 初始化数组
declare -a files

# 读取目录中的文件名并提取编号
for file in "$DIR"/*; do
    if [[ $file =~ 第([0-9]{4})话 ]]; then
        num=${BASH_REMATCH[1]}
        files+=($num)
    fi
done

# 排序数组
IFS=$'\n' sorted=($(sort <<<"${files[*]}"))
unset IFS

# 找出缺失的编号
missing=()
max_num=${sorted[-1]}

for ((i=1; i<=$max_num; i++)); do
    num=$(printf "%04d" $i)
    if ! [[ " ${sorted[@]} " =~ " ${num} " ]]; then
        missing+=($num)
    fi
done

# 输出到文件
{
    for num in "${missing[@]}"; do
        echo "第${num}话缺失"
    done
} > "$OUTPUT"

echo "缺失的话数已经输出到 $OUTPUT"
