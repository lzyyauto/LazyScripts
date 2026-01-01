#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEL_HIDE_SCRIPT="$SCRIPT_DIR/del_hide_file.sh"
CLEAN_EMPTY_SCRIPT="$SCRIPT_DIR/clean_empty_folder.sh"

usage() {
    echo "用法: $0 <目录路径>"
    echo "详细流程:"
    echo "  1. 调用 del_hide_file.sh 删除所有隐藏文件"
    echo "  2. 调用 clean_empty_folder.sh 清理所有空文件夹"
    echo ""
    echo "示例: $0 /mnt/user/Downloads"
    exit 0
}

# 检查参数
if [ "$#" -ne 1 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    usage
fi

TARGET_DIR="$1"

# 检查目标目录
if [ ! -d "$TARGET_DIR" ]; then
    echo "错误: 目录 '$TARGET_DIR' 不存在"
    exit 1
fi

echo "--- 开始联合清理任务 ---"
echo "目标目录: $TARGET_DIR"

# 1. 删除隐藏文件
if [ -f "$DEL_HIDE_SCRIPT" ]; then
    echo "[步骤 1/2] 正在删除隐藏文件..."
    bash "$DEL_HIDE_SCRIPT" "$TARGET_DIR"
else
    echo "错误: 找不到脚本 $DEL_HIDE_SCRIPT"
    exit 1
fi

# 2. 清理空目录
if [ -f "$CLEAN_EMPTY_SCRIPT" ]; then
    echo "[步骤 2/2] 正在清理空目录..."
    bash "$CLEAN_EMPTY_SCRIPT" "$TARGET_DIR"
else
    echo "错误: 找不到脚本 $CLEAN_EMPTY_SCRIPT"
    exit 1
fi

echo "--- 联合清理完成 ---"
