#!/bin/bash

# 指定需要遍历的根目录，使用"."表示当前目录，你可以根据需要修改
root_dir="."

# 使用find命令遍历指定目录下的所有文件和文件夹
# 排除./Pic文件夹及其子文件夹，并将输出重定向到当前目录下的files.txt文件
find "$root_dir" \( -path "./Pic" -prune \) -o -print > files.txt

echo "All files and directories, excluding ./Pic, have been listed in files.txt"
