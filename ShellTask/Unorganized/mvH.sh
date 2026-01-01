# 进入 A 文件夹
cd /mnt/user/Repository/ACG/Hcomic

for folder in */; do
  case "$folder" in
    2204室的故事|30CM立约人*|秋日天空|十億風騷*|朋友的妻子*|丑闻*|H*|Dream*|Kill*)
      ;;
    *)
      # 移动其他文件夹到 P 文件夹
      mv "$folder" /mnt/user/Repository/ACG/H
      ;;
  esac
done
