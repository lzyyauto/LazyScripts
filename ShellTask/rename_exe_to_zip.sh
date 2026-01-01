#!/bin/bash

# 检查是否提供了源文件夹路径参数
if [ $# -lt 1 ]; then
  echo "Usage: $0 <source_directory>"
  exit 1
fi

# 使用传入的参数作为源文件夹路径
source_directory="$1"
target_directory="/mnt/user/Downloads/98.temp"  # 请替换为B文件夹的实际路径

# 检查源文件夹是否存在
if [ ! -d "$source_directory" ]; then
  echo "Source directory not found: $source_directory"
  exit 1
fi

# 检查目标文件夹是否存在，不存在则创建
if [ ! -d "$target_directory" ]; then
  echo "Target directory not found, creating: $target_directory"
  mkdir -p "$target_directory"
fi

# 遍历源文件夹中的所有 .exe 文件并移动到目标文件夹
echo "Moving .exe files from $source_directory to $target_directory..."
for file in "$source_directory"/*.exe; do
  if [ -f "$file" ]; then
    mv -- "$file" "$target_directory/"
    echo "Moved $(basename "$file") to $target_directory"
  fi
done

# 切换到目标文件夹
cd "$target_directory" || { echo "Failed to switch to target directory: $target_directory"; exit 1; }

# 遍历目标文件夹中的 .exe 文件并将扩展名改为 .zip
echo "Renaming .exe files to .zip in $target_directory..."
for file in *.exe; do
  if [ -f "$file" ]; then
    mv -- "$file" "${file%.exe}.zip"
    echo "Renamed $file to ${file%.exe}.zip"
  fi
done

echo "Script completed successfully."
