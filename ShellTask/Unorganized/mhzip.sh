k#!/bin/bash

# 设置要压缩的目录的路径
parent_dir="/mnt/user/Repository/ACG/comic/星期一的丰满/"

# 检查目录是否存在
if [ ! -d "$parent_dir" ]; then
    echo "错误：目录 '$parent_dir' 不存在。"
    exit 1
fi

# 切换到父目录
cd "$parent_dir" || exit

# 遍历父目录下的所有子目录
for dir in */; do
    # 获取目录名并去除尾部斜杠
    base=$(basename "$dir")
    # 压缩子目录到zip文件，文件名使用目录名
    zip -r "${base}.zip" "$dir" && echo "压缩成功: ${base}.zip"
    # 检查zip命令的退出状态
    if [ $? -eq 0 ]; then
        # 打印当前工作目录
        echo "当前工作目录: $(pwd)"
        # 删除原子目录
        rm -rf "$dir"
        if [ $? -eq 0 ]; then
            echo "已删除原目录: $dir"
        else
            echo "删除目录失败: $dir"
        fi
    else
        echo "压缩失败: $dir"
    fi
done

