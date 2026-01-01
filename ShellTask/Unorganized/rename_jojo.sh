#!/bin/bash

# 进入包含JOJO漫画文件的目录
cd /mnt/user/Repository/ACG/comic/JOJO的奇妙冒險

# 处理包含“飆馬野郞”的文件
for file in *飆馬野郞*.zip; do
    # 使用sed提取卷号
    vol_number=$(echo "$file" | sed -n 's/.*Vol_\([0-9]*\).zip/\1/p')
    # 构建新文件名
    new_name="[Comic][JOJO的奇妙冒險][Part07][飆馬野郞]Vol_${vol_number}.zip"
    # 重命名文件
    mv "$file" "$new_name"
    echo "Renamed $file to $new_name"
done

# 处理包含“STONE OCEAN”的文件
for file in *石之海*.zip; do
    # 使用sed提取卷号
    vol_number=$(echo "$file" | sed -n 's/.*Vol_\([0-9]*\).zip/\1/p')
    # 构建新文件名
    new_name="[Comic][JOJO的奇妙冒險][Part06][石之海]Vol_${vol_number}.zip"
    # 重命名文件
    mv "$file" "$new_name"
    echo "Renamed $file to $new_name"
done
