#!/bin/bash

# ================= 配置默认值 =================
HOST="unl"
REMOTE_BASE="/data"
DRY_RUN=false
SRC_DIR=""
BLACKLIST_WORD=""  # 黑名单默认为空
MAPPING_FILE="upload_sync.txt"

# ================= 颜色定义 =================
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# ================= 帮助信息 =================
show_help() {
    echo -e "${BLUE}scp_upload.sh - 文件夹自动分类并远程上传脚本${NC}"
    echo ""
    echo -e "${YELLOW}用法:${NC}"
    echo "  ./scp_upload.sh -s <源目录> [选项]"
    echo ""
    echo -e "${YELLOW}选项:${NC}"
    echo -e "  ${GREEN}-s, --source <dir>${NC}      本地源目录 (必填)。脚本会遍历此目录下的所有子文件夹。"
    echo -e "  ${GREEN}-d, --dest <remote_dir>${NC} 远程目标根目录 (默认: /data)。"
    echo -e "  ${GREEN}-h, --host <ssh_host>${NC}   SSH 目标主机 (默认: unl)。"
    echo -e "  ${GREEN}-b, --blacklist <word>${NC}  黑名单关键词。包含该词的文件夹将被跳过。"
    echo -e "  ${GREEN}-m, --mapping <file>${NC}    同步文件路径 (默认: upload_sync.txt)。"
    echo -e "  ${GREEN}--dry-run${NC}             测试模式。仅显示将要执行的操作，不实际上传。"
    echo -e "  ${GREEN}-?, --help${NC}            显示此帮助信息。"
    echo ""
    echo -e "${YELLOW}功能说明:${NC}"
    echo "  1. 脚本会扫描指定的源目录下的每一级子文件夹。"
    echo "  2. 自动维护一个同步文件 (默认 upload_sync.txt):"
    echo "     - MAP:作者|目标  -> 用于作者级批量分类，修改目标值可改变该作者所有文件夹的上传路径。"
    echo "     - OK:文件夹名称 -> 用于记录已上传历史，自动跳过。"
    echo "  3. 使用 rsync 将文件夹上传到远程目录。"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  ./scp_upload.sh -s ./my_photos --dry-run"
    echo "  ./scp_upload.sh -s /source/path -d /remote/path -h my_server -b \"temp\""
    echo ""
}

# ================= 解析参数 =================
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -s|--source) SRC_DIR="$2"; shift ;;
        -d|--dest) REMOTE_BASE="$2"; shift ;;
        -h|--host) HOST="$2"; shift ;;
        -b|--blacklist) BLACKLIST_WORD="$2"; shift ;; # 新增参数
        -m|--mapping) MAPPING_FILE="$2"; shift ;;
        --dry-run) DRY_RUN=true ;;
        -\?|--help) show_help; exit 0 ;;
        *) echo -e "${RED}未知参数: $1${NC}"; show_help; exit 1 ;;
    esac
    shift
done

if [ -z "$SRC_DIR" ]; then 
    echo -e "${RED}错误: 请指定源目录 -s${NC}"
    echo ""
    show_help
    exit 1
fi

# 去掉远程目录末尾的斜杠
REMOTE_BASE="${REMOTE_BASE%/}"

echo "----------------------------------------"
echo -e "目标主机: ${GREEN}$HOST${NC}"
echo -e "本地目录: ${GREEN}$SRC_DIR${NC}"
echo -e "远程目录: ${GREEN}$REMOTE_BASE${NC}"
echo -e "映射文件: ${GREEN}$MAPPING_FILE${NC}"
if [ -n "$BLACKLIST_WORD" ]; then
    echo -e "黑名单关键词: ${RED}$BLACKLIST_WORD${NC}"
fi
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}>>> 测试模式 (Dry Run) <<<${NC}"
fi
echo "----------------------------------------"

cd "$SRC_DIR" || exit

count=0

# 遍历目录
for folder in */; do
    folder="${folder%/}" # 去掉本地文件夹末尾斜杠
    if [ ! -d "$folder" ]; then continue; fi

    ((count++))

    # ================= 黑名单检查 =================
    # 如果设置了黑名单，且文件夹名包含该词
    if [ -n "$BLACKLIST_WORD" ]; then
        if [[ "$folder" == *"$BLACKLIST_WORD"* ]]; then
            echo -e "[${count}] ${RED}[跳过/Skip]${NC} 命中黑名单: ${folder}"
            continue
        fi
    fi
    # ============================================

    # ================= 同步与历史检查 =================
    touch "$MAPPING_FILE"
    
    # 1. 检查历史 (OK:文件夹名)
    if grep -q "^OK:${folder}$" "$MAPPING_FILE"; then
        echo -e "[${count}] ${YELLOW}[跳过/Done]${NC} 记录显示已完成: ${folder}"
        continue
    fi

    # 2. 解析原始作者名
    if [[ "$folder" == *" - "* ]]; then
        raw_author="${folder%% - *}"
    else
        raw_author="${folder%% *}"
    fi

    # 3. 检查作者映射 (MAP:原始作者名|目标作者名)
    author_map=$(grep "^MAP:${raw_author}|" "$MAPPING_FILE")
    
    if [ -n "$author_map" ]; then
        # 如果找到映射，提取目标作者名
        author=$(echo "$author_map" | cut -d'|' -f2)
        if [ "$author" != "$raw_author" ]; then
            echo -e "[${count}] ${BLUE}[匹配/Alias]${NC} 作者 ${raw_author} -> ${author}"
        else
            echo -e "[${count}] 处理: ${BLUE}${folder}${NC}"
        fi
    else
        # 如果未找到映射，使用解析出的名字并存入映射文件
        author="$raw_author"
        echo "MAP:${raw_author}|${author}" >> "$MAPPING_FILE"
        echo -e "[${count}] ${GREEN}[新作者/New]${NC} 已记录别名关系: ${raw_author} -> ${author}"
    fi
    # ================================================

    # 构建远程路径
    remote_author_dir="${REMOTE_BASE}/${author}"
    echo -e "    目标父级: ${remote_author_dir}"

    if [ "$DRY_RUN" = true ]; then
        echo -e "    ${YELLOW}[测试] mkdir -p '${remote_author_dir}'${NC}"
        echo -e "    ${YELLOW}[测试] rsync ... '${remote_author_dir}/'${NC}"
    else
        # 1. 创建远程目录
        ssh "$HOST" "export LC_ALL=en_US.UTF-8; mkdir -p '$remote_author_dir'"
        
        if [ $? -ne 0 ]; then
            echo -e "    ${RED}[错误] 创建目录失败，检查连接或权限${NC}"
            continue
        fi

        # 2. rsync 上传
        rsync -avP "$folder" "$HOST:'$remote_author_dir/'"
        
        if [ $? -eq 0 ]; then
            echo -e "    ${GREEN}成功${NC}"
            # 记录到历史
            echo "OK:${folder}" >> "$MAPPING_FILE"
        else
            echo -e "    ${RED}上传失败${NC}"
        fi
    fi
    echo "----------------------------------------"
done