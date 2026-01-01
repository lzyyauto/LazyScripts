#!/bin/bash

# 检查是否提供了目录路径和密码参数
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 [directory] [password]"
  exit 1
fi

# 获取传递的目录路径和密码
target_directory="$1"
password="$2"

# 切换到目标目录
cd "$target_directory" || { echo "Directory not found: $target_directory"; exit 1; }

# 遍历所有的 .zip 文件并使用提供的密码进行解压
for file in *.zip; do
  if [ -f "$file" ]; then
    unzip -P "$password" "$file" -d "${file%.zip}"
    if [ $? -eq 0 ]; then
      echo "Successfully extracted $file to ${file%.zip}/"
    else
      echo "Failed to extract $file"
    fi
  fi
done
