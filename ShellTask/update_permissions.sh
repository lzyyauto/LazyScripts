#!/bin/bash

# 检查是否传入参数
if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# 获取传入的目录
TARGET_DIR="$1"

# 检查目录是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

# 设置用户组
USER_GROUP="nobody:users"

# 生成带日期的日志文件名
LOG_FILE="update_permissions_$(date +'%Y%m%d_%H%M%S').log"
echo "Log file: $LOG_FILE"
echo "Processing directory: $TARGET_DIR" > "$LOG_FILE"

# 统计总数
TOTAL_ITEMS=$(find "$TARGET_DIR" \( -type f -o -type d \) | wc -l)
echo "Total items to process: $TOTAL_ITEMS" | tee -a "$LOG_FILE"

# 初始化进度
CURRENT=0

# 遍历文件和目录
echo "Processing files and directories..."
find "$TARGET_DIR" \( -type f -o -type d \) | while read -r ITEM; do
    CURRENT=$((CURRENT + 1))
    
    if [ -f "$ITEM" ]; then
        chown "$USER_GROUP" "$ITEM"
        chmod 640 "$ITEM"
        TYPE="File"
    elif [ -d "$ITEM" ]; then
        chown "$USER_GROUP" "$ITEM"
        chmod 777 "$ITEM"
        TYPE="Directory"
    fi

    echo "[$CURRENT/$TOTAL_ITEMS] Processed $TYPE: $ITEM" | tee -a "$LOG_FILE"
done

echo "Processing complete! See $LOG_FILE for details."
