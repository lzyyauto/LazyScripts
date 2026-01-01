#!/bin/bash

# 指定文件夹路径
TARGET_DIR="$1"
# 指定前缀
PREFIX="$2"

# 检查是否提供了文件夹路径和前缀
if [ -z "$TARGET_DIR" ] || [ -z "$PREFIX" ]; then
  echo "Usage: $0 <directory> <prefix>"
  exit 1
fi

# 检查目标是否为文件夹
if [ ! -d "$TARGET_DIR" ]; then
  echo "Error: $TARGET_DIR is not a directory"
  exit 1
fi

# 遍历目标文件夹中的所有文件
for FILE in "$TARGET_DIR"/*; do
  # 获取文件名
  BASENAME=$(basename "$FILE")
  # 获取新的文件名
  NEW_NAME="$TARGET_DIR/$PREFIX$BASENAME"
  # 重命名文件
  mv "$FILE" "$NEW_NAME"
done

echo "All files in $TARGET_DIR have been renamed with prefix $PREFIX"
