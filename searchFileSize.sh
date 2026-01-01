#!/bin/bash

# 脚本功能：统计指定文件夹中视频文件的大小并排序
# Script: Search and sort video files by size

# 默认参数 / Default parameters
SEARCH_DIR="."
SORT_ORDER="desc"  # desc: 降序(从大到小), asc: 升序(从小到大)
TOP_N=100
EXCLUDE_PATTERNS=()
VIDEO_EXTENSIONS=("mp4" "avi" "mkv" "mov" "wmv" "flv" "webm" "m4v" "mpg" "mpeg" "3gp" "ts" "rmvb" "rm")

# 颜色定义 / Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息 / Show help message
show_help() {
    cat << EOF
${GREEN}视频文件大小统计工具 / Video File Size Statistics Tool${NC}

用法 / Usage:
    $0 [选项] [目录]

选项 / Options:
    -d, --dir <目录>          指定搜索目录 (默认: 当前目录)
                              Specify search directory (default: current directory)
    
    -s, --sort <order>        排序方式: desc(降序/从大到小) 或 asc(升序/从小到大)
                              Sort order: desc (descending) or asc (ascending)
                              默认 / Default: desc
    
    -n, --top <数量>          显示前N个结果 (默认: 100)
                              Show top N results (default: 100)
    
    -e, --exclude <模式>      排除匹配的文件/文件夹 (可多次使用)
                              Exclude files/folders matching pattern (can be used multiple times)
                              示例 / Example: -e "*/node_modules/*" -e "*.tmp"
    
    -x, --extensions <ext>    自定义视频扩展名 (逗号分隔)
                              Custom video extensions (comma separated)
                              默认 / Default: mp4,avi,mkv,mov,wmv,flv,webm,m4v,mpg,mpeg,3gp,ts,rmvb,rm
    
    -h, --help               显示此帮助信息
                              Show this help message

示例 / Examples:
    # 搜索当前目录，显示前100个最大的视频文件
    $0
    
    # 搜索指定目录，显示前50个最大的视频文件
    $0 -d /path/to/videos -n 50
    
    # 按升序排序（从小到大）
    $0 -s asc
    
    # 排除特定文件夹
    $0 -e "*/backup/*" -e "*/temp/*"
    
    # 自定义视频扩展名
    $0 -x "mp4,mkv,avi"

EOF
}

# 解析命令行参数 / Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dir)
            SEARCH_DIR="$2"
            shift 2
            ;;
        -s|--sort)
            SORT_ORDER="$2"
            shift 2
            ;;
        -n|--top)
            TOP_N="$2"
            shift 2
            ;;
        -e|--exclude)
            EXCLUDE_PATTERNS+=("$2")
            shift 2
            ;;
        -x|--extensions)
            IFS=',' read -ra VIDEO_EXTENSIONS <<< "$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            # 如果没有 - 开头，当作目录处理
            if [[ ! "$1" =~ ^- ]]; then
                SEARCH_DIR="$1"
                shift
            else
                echo -e "${RED}错误: 未知选项 $1${NC}" >&2
                echo "使用 -h 或 --help 查看帮助信息"
                exit 1
            fi
            ;;
    esac
done

# 验证搜索目录 / Validate search directory
if [[ ! -d "$SEARCH_DIR" ]]; then
    echo -e "${RED}错误: 目录不存在: $SEARCH_DIR${NC}" >&2
    exit 1
fi

# 验证排序方式 / Validate sort order
if [[ "$SORT_ORDER" != "desc" && "$SORT_ORDER" != "asc" ]]; then
    echo -e "${RED}错误: 排序方式必须是 'desc' 或 'asc'${NC}" >&2
    exit 1
fi

# 验证数量 / Validate top N
if ! [[ "$TOP_N" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}错误: 数量必须是正整数${NC}" >&2
    exit 1
fi

# 构建 find 命令的扩展名参数 / Build find command extension parameters
find_extensions=""
for i in "${!VIDEO_EXTENSIONS[@]}"; do
    ext="${VIDEO_EXTENSIONS[$i]}"
    if [[ $i -eq 0 ]]; then
        find_extensions="-iname \"*.$ext\""
    else
        find_extensions="$find_extensions -o -iname \"*.$ext\""
    fi
done

# 构建排除参数 / Build exclude parameters
exclude_cmd=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    exclude_cmd="$exclude_cmd ! -path \"$pattern\""
done

# 显示搜索信息 / Show search information
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}视频文件大小统计${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "搜索目录 / Search Directory: ${YELLOW}$SEARCH_DIR${NC}"
echo -e "排序方式 / Sort Order: ${YELLOW}$SORT_ORDER${NC}"
echo -e "显示数量 / Top N: ${YELLOW}$TOP_N${NC}"
echo -e "视频扩展名 / Video Extensions: ${YELLOW}${VIDEO_EXTENSIONS[*]}${NC}"
if [[ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]]; then
    echo -e "排除模式 / Exclude Patterns: ${YELLOW}${EXCLUDE_PATTERNS[*]}${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

# 创建临时文件 / Create temporary file
temp_file=$(mktemp)
trap "rm -f $temp_file" EXIT

# 执行搜索 / Execute search
echo -e "${GREEN}正在搜索视频文件...${NC}"
eval "find \"$SEARCH_DIR\" -type f $exclude_cmd \\( $find_extensions \\) -exec ls -l {} \\;" 2>/dev/null | \
    awk '{
        size = $5
        # 从第9列开始是文件名（可能包含空格）
        filename = ""
        for (i=9; i<=NF; i++) {
            filename = filename (i==9 ? "" : " ") $i
        }
        print size "\t" filename
    }' > "$temp_file"

# 检查是否找到文件 / Check if files found
file_count=$(wc -l < "$temp_file" | tr -d ' ')
if [[ $file_count -eq 0 ]]; then
    echo -e "${YELLOW}未找到任何视频文件${NC}"
    exit 0
fi

echo -e "${GREEN}找到 $file_count 个视频文件${NC}"
echo ""

# 排序并显示结果 / Sort and display results
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}文件大小排序结果 (前 $TOP_N 个)${NC}"
echo -e "${BLUE}========================================${NC}"
printf "${YELLOW}%-15s %-15s %s${NC}\n" "大小/Size" "可读大小/Human" "文件路径/File Path"
echo -e "${BLUE}----------------------------------------${NC}"

# 根据排序方式选择 sort 参数 / Choose sort parameter based on sort order
if [[ "$SORT_ORDER" == "desc" ]]; then
    sort_param="-rn"
else
    sort_param="-n"
fi

# 人性化显示文件大小的函数 / Function to display human-readable file size
human_readable_size() {
    local size=$1
    if [[ $size -lt 1024 ]]; then
        echo "${size}B"
    elif [[ $size -lt 1048576 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1024}")KB"
    elif [[ $size -lt 1073741824 ]]; then
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1048576}")MB"
    else
        echo "$(awk "BEGIN {printf \"%.2f\", $size/1073741824}")GB"
    fi
}

# 排序并显示 / Sort and display
sort $sort_param "$temp_file" | head -n "$TOP_N" | while IFS=$'\t' read -r size filepath; do
    human_size=$(human_readable_size "$size")
    printf "%-15s %-15s %s\n" "$size" "$human_size" "$filepath"
done

echo -e "${BLUE}========================================${NC}"

# 统计总大小 / Calculate total size
total_size=$(sort $sort_param "$temp_file" | head -n "$TOP_N" | awk '{sum+=$1} END {print sum}')
total_human=$(human_readable_size "$total_size")

echo ""
echo -e "${GREEN}统计信息 / Statistics:${NC}"
echo -e "  显示文件数 / Files Shown: ${YELLOW}$(sort $sort_param "$temp_file" | head -n "$TOP_N" | wc -l | tr -d ' ')${NC}"
echo -e "  总文件数 / Total Files: ${YELLOW}$file_count${NC}"
echo -e "  显示文件总大小 / Total Size (Shown): ${YELLOW}$total_size bytes ($total_human)${NC}"
