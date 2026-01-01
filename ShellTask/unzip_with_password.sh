#!/bin/bash

# 检查是否提供了目录路径参数
if [ -z "$1" ]; then
  echo "未提供目录路径，将使用当前目录。"
  TARGET_DIR="."
else
  TARGET_DIR="$1"
fi

# 默认密码
PASSWORD="reduwallpaper"

# 检查目标目录是否存在
if [ ! -d "$TARGET_DIR" ]; then
  echo "错误：目录 $TARGET_DIR 不存在！"
  exit 1
fi

# 遍历目标目录中的所有 ZIP 文件并解压
for ZIP_FILE in "$TARGET_DIR"/*.zip; do
  if [ -f "$ZIP_FILE" ]; then
    echo "正在解压：$ZIP_FILE"
    unzip -P "$PASSWORD" "$ZIP_FILE" -d "$TARGET_DIR"
  fi
done

echo "解压完成！"
