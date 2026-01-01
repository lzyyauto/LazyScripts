#!/bin/bash

# 配置
PID_FILE="/tmp/backup_immich.pid"
FOLDER_TO_COMPRESS="/mnt/user/Immich/library/admin"
LOG_DIR="/mnt/user/Repository/ShellTask/tmp"

# Function to display usage help
usage() {
    echo "用法: $0 [-h] [-f] [-s]"
    echo "这个脚本用于压缩 Immich 媒体库文件夹，并将其保存到指定位置。"
    echo "默认情况下，脚本会自动重定向到后台运行 (nohup)。"
    echo ""
    echo "选项:"
    echo "  -h    显示此帮助信息并退出。"
    echo "  -f    在前台运行脚本 (不强制 nohup)。"
    echo "  -s    停止正在运行的后台备份任务。"
    exit 0
}

# 停止任务逻辑
stop_task() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "检测到正在运行的任务 (PID: $PID)，正在尝试停止..."
        # 杀死进程组以确保子进程（如 zip）也被终止
        kill -TERM -"$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "任务已停止。"
    else
        echo "未检测到正在运行的任务。"
    fi
    exit 0
}

# 解析 -s 选项 (在自动 nohup 之前处理)
if [[ "$1" == "-s" ]]; then
    stop_task
fi

# 自动 nohup 逻辑
if [[ "$1" != "-f" && "$1" != "-h" && -z "$IS_NOHUP_RUNNING" ]]; then
    # 检查是否已经在运行
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "错误: 备份任务已在运行 (PID: $PID)。请先使用 -s 停止，或等待完成。"
            exit 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "检测到未在后台运行，正在自动以 nohup 启动..."
    TIMESTAMP=$(date +%Y%m%d%H%M)
    INITIAL_LOG="$LOG_DIR/immich_${TIMESTAMP}.log"
    export IS_NOHUP_RUNNING=1
    # 使用 setsid 或类似方式确保我们可以杀死进程组
    nohup "$0" "$@" >> "$INITIAL_LOG" 2>&1 &
    echo "脚本已在后台启动。"
    echo "日志查看: $INITIAL_LOG"
    echo "停止任务: $0 -s"
    exit 0
fi

# Parse command-line options
while getopts "hf" opt; do
    case ${opt} in
        h) usage ;;
        f) ;; # 已处理
        \?) echo "无效选项" >&2; usage ;;
    esac
done
shift $((OPTIND - 1))

# --- 开始执行备份任务 (IS_NOHUP_RUNNING 模式或 -f 模式) ---

# 记录 PID
echo $$ > "$PID_FILE"

# 清理函数
cleanup() {
    rm -f "$PID_FILE"
}
trap cleanup EXIT SIGINT SIGTERM

TIMESTAMP=$(date +%Y%m%d%H%M)
OUTPUT_FILE="$LOG_DIR/immich_${TIMESTAMP}.zip"
LOG_FILE="$LOG_DIR/immich_${TIMESTAMP}.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting compression..." >> "$LOG_FILE"

if [ ! -d "$FOLDER_TO_COMPRESS" ]; then
    echo "Error: Directory $FOLDER_TO_COMPRESS does not exist." >> "$LOG_FILE"
    exit 1
fi

total_files=$(find "$FOLDER_TO_COMPRESS" -type f | wc -l)
if [ "$total_files" -eq 0 ]; then
    echo "No files found to compress." >> "$LOG_FILE"
    exit 1
fi

count=0
# 运行压缩并记录进度
zip -r "$OUTPUT_FILE" "$FOLDER_TO_COMPRESS" -x '*.DS_Store' -x '__MACOSX' | while read line; do
    ((count++))
    # 每 100 个文件更新一次进度，避免写入过于频繁
    if (( count % 500 == 0 )); then
        echo "Progress: $((count * 100 / total_files))% ($count/$total_files)" >> "$LOG_FILE"
    fi
done

if [ -f "$OUTPUT_FILE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Compression completed successfully. Output: $OUTPUT_FILE" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Error: Compression failed." >> "$LOG_FILE"
fi
