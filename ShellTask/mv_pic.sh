#!/bin/bash

# 设置源目录和目标目录
SOURCE_DIR="/mnt/user/Downloads/96.win/Pic"
TARGET_DIR="/mnt/user/Machine learning/Pic"

# 确保目录存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "错误: 源目录 '$SOURCE_DIR' 不存在"
    exit 1
fi

# 创建日志文件
LOG_FILE="file_organizer_$(date +%Y%m%d_%H%M%S).log"
touch "$LOG_FILE"

log_message() {
    local message="$1"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $message" | tee -a "$LOG_FILE"
}

log_message "开始处理文件夹..."
log_message "源目录: $SOURCE_DIR"
log_message "目标目录: $TARGET_DIR"

# 打印一个文件夹的调试信息
debug_folder() {
    local folder_name="$1"
    log_message "调试: 处理文件夹 \"$folder_name\""
}

# 遍历源目录中的所有文件夹
find "$SOURCE_DIR" -maxdepth 1 -type d ! -path "$SOURCE_DIR" | while read -r folder; do
    # 获取文件夹名称
    folder_name=$(basename "$folder")
    
    # 调试信息
    debug_folder "$folder_name"
    
    # 提取作者名称的正则表达式
    # 优先级：
    # 1. 匹配 "作者名 - NO." 模式
    # 2. 匹配 "作者名 \ NO." 模式
    # 3. 如果含有连字符，但没有NO.，取第一个连字符之前的部分（作者名 - 作品名）
    # 4. 取第一个非数字和标点的部分
    
    if [[ $folder_name =~ ^(.*?)[[:space:]]*[-–—][[:space:]]*NO\. ]]; then
        author="${BASH_REMATCH[1]}"
        log_message "调试: 匹配了模式1 - \"$author\""
    elif [[ $folder_name =~ ^(.*?)[[:space:]]*[\\][[:space:]]*NO\. ]]; then
        author="${BASH_REMATCH[1]}"
        log_message "调试: 匹配了模式2 - \"$author\""
    elif [[ $folder_name =~ ^([^-–—]+)[[:space:]]*[-–—] ]]; then
        author="${BASH_REMATCH[1]}"
        log_message "调试: 匹配了模式3 - \"$author\""
    elif [[ $folder_name =~ ^([^0-9\[\]().,:;\"\{\}\/\\]+) ]]; then
        author="${BASH_REMATCH[1]}"
        log_message "调试: 匹配了模式4 - \"$author\""
    else
        author="$folder_name"
        log_message "调试: 使用默认名称 - \"$author\""
    fi
    
    # 只清理作者名称的前后空格
    author=$(echo "$author" | sed -E "s/^[[:space:]]*//; s/[[:space:]]*$//" | xargs)
    log_message "调试: 最终作者名 - \"$author\""
    
    # 创建作者目录（如果不存在）
    author_dir="$TARGET_DIR/$author"
    if [ ! -d "$author_dir" ]; then
        mkdir -p "$author_dir"
        log_message "创建作者目录: $author"
    fi
    
    # 移动文件夹到作者目录
    if mv "$folder" "$author_dir/"; then
        log_message "成功移动: \"$folder_name\" -> \"$author/$folder_name\""
    else
        log_message "错误: 移动失败 \"$folder_name\""
    fi
done

log_message "处理完成"

# 输出统计信息
total_processed=$(grep -c "成功移动:" "$LOG_FILE")
total_warnings=$(grep -c "警告:" "$LOG_FILE")
total_errors=$(grep -c "错误:" "$LOG_FILE")

log_message "统计信息:"
log_message "- 成功处理: $total_processed 个文件夹"
log_message "- 警告: $total_warnings 个"
log_message "- 错误: $total_errors 个"
