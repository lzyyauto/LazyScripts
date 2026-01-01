#!/bin/bash

# 函数: 显示帮助信息
display_help() {
    echo "使用方法: $0 [选项] <目录路径>"
    echo "清理指定目录及其子目录中的所有空文件夹。"
    echo ""
    echo "选项:"
    echo "  -h, --help    显示此帮助信息并退出"
    echo ""
    echo "示例:"
    echo "  $0 /path/to/your/directory"
    echo "  $0 -h"
    exit 0
}

# 检查是否提供了目录参数或帮助选项
if [ $# -eq 0 ]; then
    display_help
fi

# 检查第一个参数是否是帮助选项
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    display_help
fi

# 检查是否提供了多余的参数
if [ $# -ne 1 ]; then
    echo "错误: 参数数量不正确。"
    display_help
fi

# 检查提供的路径是否存在且是目录
if [ ! -d "$1" ]; then
    echo "错误: '$1' 不是一个有效的目录"
    exit 1
fi

# 将输入路径规范化,移除末尾的斜杠
input_dir=$(echo "$1" | sed 's:/*$::')

# 函数: 检查目录是否为空 (考虑所有文件和子目录,包括隐藏的)
# rmdir 命令只删除真正空的目录 (不包含任何文件或子目录,包括隐藏的)
is_dir_empty() {
    local dir="$1"
    # 检查目录内除了 '.' 和 '..' 之外是否有其他条目
    # find -maxdepth 1 -mindepth 1 会列出所有直接子项 (文件或目录)
    # -print -quit 找到第一个就退出,提高效率
    local count=$(find "$dir" -maxdepth 1 -mindepth 1 -print -quit | wc -l)
    if [ "$count" -eq 0 ]; then
        return 0    # 目录为空
    else
        return 1    # 目录不为空
    fi
}

# 函数: 递归检查并删除空目录
remove_empty_dirs() {
    local dir="$1"
    local empty=true
    
    # Enable nullglob to prevent "$dir/*" from expanding to literal "*" if directory is empty
    local old_nullglob_setting=$(shopt -p nullglob) # Save current setting
    shopt -s nullglob
    
    # 遍历所有子目录和文件
    for item in "$dir"/*; do
        if [ -d "$item" ]; then
            # 递归处理子目录
            remove_empty_dirs "$item"
            
            # 如果子目录仍然存在(即不为空),则当前目录不为空
            if [ -d "$item" ]; then
                empty=false
            fi
        else # If it's a file
            # 如果存在任何文件,则目录不为空
            empty=false
        fi
    done
    
    # Restore nullglob setting
    eval "$old_nullglob_setting"
    
    # 检查当前目录是否为空
    if $empty && is_dir_empty "$dir" && [ "$dir" != "$input_dir" ]; then
        echo "尝试删除目录: $dir"
        if rmdir "$dir" 2>/dev/null; then
            echo "  成功删除: $dir"
        else
            echo "  未能删除 (可能不为空或权限问题): $dir"
        fi
    fi
}

# 开始执行清理
echo "开始检查目录: $input_dir"
remove_empty_dirs "$input_dir"
echo "完成清理"
