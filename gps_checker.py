#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片 GPS 信息处理工具 (gps_tool.py) V1.6

功能:
1.  扫描指定文件夹中的图片 (JPG, JPEG, TIF, TIFF)。
2.  检查每张图片是否包含 EXIF GPS 信息。
3.  (可选) 显示图片的 GPS 坐标 (处理多种 EXIF 格式)。
4.  (可选) 将没有 GPS 信息的图片移动到子文件夹。
5.  (可选) 从 CSV 日志文件读取 GPS 数据 (识别 'datatime', 使用本地时间)。
6.  (可选) 根据时间戳为图片添加/更新 GPS 数据 (包括位置和时间戳)。
7.  (可选) 将处理结果输出到文件。

支持命令行参数和交互式模式运行。
"""

import argparse
import bisect
import csv
import os
import sys
from datetime import datetime, timedelta
import concurrent.futures # 添加 concurrent.futures 导入

try:
    import piexif
except ImportError:
    print("[错误] 缺少 'piexif' 库。请运行: pip install piexif")
    sys.exit(1)
try:
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS
except ImportError:
    print("[错误] 缺少 'Pillow' 库。请运行: pip install Pillow")
    sys.exit(1)

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("[警告] 未找到 'pillow-heif' 库。HIF/HEIC 文件可能无法处理。")
    print("       如需支持 HIF/HEIC, 请运行: pip install pillow-heif")

# --- 全局常量 ---
SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.tif', '.tiff', '.hif', '.heic')
DEFAULT_TOLERANCE_SECONDS = 300 # 默认时间匹配容差 (秒)

# ============================================
# == GPS 坐标转换函数
# ============================================


def _convert_to_degrees(value):
    """(内部) 将 GPS 元组 (度, 分, 秒) 转换为十进制 (处理多种格式)"""
    try:
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise TypeError(f"GPS值不是包含3个元素的元组/列表: {value}")
        first_element = value[0]
        if isinstance(first_element,
                      (tuple, list)) and len(first_element) == 2:
            if not (isinstance(value[1], (tuple, list)) and len(value[1]) == 2
                    and isinstance(value[2],
                                   (tuple, list)) and len(value[2]) == 2):
                raise TypeError(f"GPS值格式不一致 (混合格式): {value}")
            d = float(value[0][0]) / float(value[0][1])
            m = float(value[1][0]) / float(value[1][1])
            s = float(value[2][0]) / float(value[2][1])
        elif isinstance(first_element, (int, float)):
            if not (isinstance(value[1], (int, float))
                    and isinstance(value[2], (int, float))):
                raise TypeError(f"GPS值格式不一致 (混合格式): {value}")
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
        elif hasattr(first_element, 'numerator') and hasattr(
                first_element, 'denominator'):
            d = float(first_element.numerator) / float(
                first_element.denominator)
            m = float(value[1].numerator) / float(value[1].denominator)
            s = float(value[2].numerator) / float(value[2].denominator)
        else:
            raise TypeError(f"未知的 GPS 值格式或结构: {value}")
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ZeroDivisionError, IndexError, AttributeError) as e:
        print(f"\n[警告] 转换度数时出错: {value} - {e}")
        return None


def convert_gps_to_decimal(gps_info):
    """将 EXIF GPS 信息转换为十进制经纬度"""
    lat = None
    lon = None
    gps_latitude = gps_info.get('GPSLatitude')
    gps_latitude_ref = gps_info.get('GPSLatitudeRef')
    gps_longitude = gps_info.get('GPSLongitude')
    gps_longitude_ref = gps_info.get('GPSLongitudeRef')
    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat_dec = _convert_to_degrees(gps_latitude)
        lon_dec = _convert_to_degrees(gps_longitude)
        if lat_dec is not None:
            lat_ref_str = gps_latitude_ref.decode('utf-8') if isinstance(
                gps_latitude_ref, bytes) else gps_latitude_ref
            lat = lat_dec if lat_ref_str == "N" else -lat_dec
        if lon_dec is not None:
            lon_ref_str = gps_longitude_ref.decode('utf-8') if isinstance(
                gps_longitude_ref, bytes) else gps_longitude_ref
            lon = lon_dec if lon_ref_str == "E" else -lon_dec
    return lat, lon


def _deg_to_dms_rational(deg_float):
    """(内部) 将十进制角度转换为 EXIF 使用的有理数 DMS 格式"""
    deg_float = abs(deg_float)
    deg = int(deg_float)
    min_float = (deg_float - deg) * 60
    min_val = int(min_float)
    sec_float = (min_float - min_val) * 60
    return ((deg, 1), (min_val, 1), (int(sec_float * 10000), 10000))


# ============================================
# == EXIF 数据处理函数
# ============================================

def get_exif_data(image_path):
    """提取图片的 EXIF 数据。优先使用 image.info['exif'] (通常为 bytes), 然后用 piexif 解析。
       如果 image.info['exif'] 不可用，则尝试 image._getexif() (Pillow 的解析结果)。
    """
    try:
        with Image.open(image_path) as image:
            image.load()  # Ensure image data is loaded

            # 优先尝试从 image.info['exif'] 获取原始 EXIF 数据 (bytes)
            # pillow-heif 插件会将 EXIF 数据放在这里
            raw_exif_bytes = image.info.get('exif')
            if raw_exif_bytes:
                try:
                    # piexif.load() 将 bytes 解析为标准的 EXIF 字典结构
                    return piexif.load(raw_exif_bytes)
                except Exception: # piexif.InvalidImageDataError or other piexif errors
                    # If piexif parsing fails, try Pillow's internal method if available
                    pass 

            # 如果 image.info['exif'] 不可用或解析失败，尝试 Pillow 自带的 _getexif()
            # 注意: HeifImageFile 对象没有 _getexif 方法，所以对于HIF文件，上面的路径理论上应成功
            if hasattr(image, '_getexif'):
                pil_exif_data = image._getexif() # Pillow 的 EXIF 解析结果，是一个平面字典 {tag_id: value}
                if pil_exif_data:
                    return pil_exif_data # 直接返回这个字典

            return None # 如果两种方法都没有获取到 EXIF 数据
    except Exception as e:
        # 捕获 Image.open 或 image.load 可能发生的错误
        print(f"\n[错误] 读取图片 {os.path.basename(image_path)} 的 EXIF 数据时出错: {e}")
        return None


def get_gps_info(exif_data):
    """从 EXIF 数据中提取 GPS 信息字典。
       可以处理 piexif.load() 的输出或 Pillow 的 _getexif() 输出。
    """
    if not exif_data:
        return None
    
    gps_ifd_data = None

    # 检查是否是 piexif.load() 的输出格式 (包含 'GPS' key)
    if 'GPS' in exif_data and isinstance(exif_data['GPS'], dict):
        gps_ifd_data = exif_data['GPS']
    # 检查是否是 Pillow 的 _getexif() 输出格式 (包含 GPSInfo tag)
    elif isinstance(exif_data, dict): # Ensure exif_data is a dict before iterating
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'GPSInfo' and isinstance(value, dict):
                gps_ifd_data = value
                break
    
    if gps_ifd_data:
        gps_info_dict = {}
        for gps_tag_id, gps_value in gps_ifd_data.items():
            gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
            gps_info_dict[gps_tag_name] = gps_value
        return gps_info_dict if gps_info_dict else None # Return None if dict is empty
        
    return None


def get_image_datetime(exif_data):
    """从 EXIF 数据中获取拍摄时间 (返回本地时间对象)
       可以处理 piexif.load() 的输出或 Pillow 的 _getexif() 输出。
    """
    if not exif_data:
        return None
    
    date_time_str = None
    # 检查 exif_data 是否是 piexif.load() 的输出格式 (结构化字典)
    if isinstance(exif_data.get('Exif'), dict):
        date_time_str = exif_data['Exif'].get(36867) # DateTimeOriginal from ExifIFD
        if not date_time_str and isinstance(exif_data.get('0th'), dict):
            date_time_str = exif_data['0th'].get(306) # DateTime from 0th IFD (ImageIFD)
    # 否则，假设是 Pillow 的 _getexif() 输出格式 (扁平字典)
    elif isinstance(exif_data, dict):
        date_time_str = exif_data.get(36867) or exif_data.get(306)

    if date_time_str:
        try:
            if isinstance(date_time_str, bytes):
                date_time_str = date_time_str.decode('utf-8')
            return datetime.strptime(date_time_str.strip(), '%Y:%m:%d %H:%M:%S')
        except (ValueError, TypeError, AttributeError) as e:
            print(f"\n[警告] 解析时间戳时出错: {date_time_str} - {e}")
    return None


def add_gps_to_image(image_path, lat, lon, alt=0.0, timestamp_dt=None):
    """将 GPS 信息写入图片文件 (包括时间戳)"""
    try:
        lat_ref = 'N' if lat >= 0 else 'S'
        lon_ref = 'E' if lon >= 0 else 'W'
        lat_dms = _deg_to_dms_rational(lat)
        lon_dms = _deg_to_dms_rational(lon)
        gps_ifd = {
            piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLatitude: lat_dms,
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLongitude: lon_dms,
            piexif.GPSIFD.GPSAltitudeRef: 0,
            piexif.GPSIFD.GPSAltitude: (int(abs(alt) * 100), 100),
        }
        if timestamp_dt:
            gps_ifd[piexif.GPSIFD.GPSTimeStamp] = ((timestamp_dt.hour, 1),
                                                   (timestamp_dt.minute, 1),
                                                   (timestamp_dt.second, 1))
            gps_ifd[piexif.GPSIFD.GPSDateStamp] = timestamp_dt.strftime(
                '%Y:%m:%d')

        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get('exif', b''))
        exif_dict['GPS'] = gps_ifd
        exif_bytes = piexif.dump(exif_dict)
        img.save(image_path, exif=exif_bytes, quality=100) # 设置JPEG保存质量为100
        ts_str = f" @ {timestamp_dt.strftime('%H:%M:%S')}" if timestamp_dt else ""
        print(
            f"\n[成功] 为 {os.path.basename(image_path)} 添加 GPS: ({lat:.6f}, {lon:.6f}){ts_str}"
        )
        return True
    except Exception as e:
        print(f"\n[错误] 为 {os.path.basename(image_path)} 添加 GPS 时出错: {e}")
        return False


# ============================================
# == CSV 数据处理函数
# ============================================


def load_gps_csv(csv_path):
    """加载并解析 GPS CSV 文件"""
    gps_data = []
    print(f"正在加载 GPS 数据文件: {csv_path}")
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
                print(f"  > CSV 表头: {header}")
            except StopIteration:
                print("[错误] GPS 数据文件为空。")
                return None

            ts_idx, lat_idx, lon_idx, alt_idx = -1, -1, -1, -1
            header_lower = [h.strip().lower() for h in header]

            possible_ts = ['timestamp', 'time', 'gpstime', '时间戳',
                           'datatime']  # <--- 添加 'datatime'
            possible_lat = ['latitude', 'lat', '纬度']
            possible_lon = ['longitude', 'lon', 'long', '经度']
            possible_alt = ['altitude', 'alt', '高度', '海拔']

            for p in possible_ts:
                if p in header_lower:
                    ts_idx = header_lower.index(p)
                    break
            for p in possible_lat:
                if p in header_lower:
                    lat_idx = header_lower.index(p)
                    break
            for p in possible_lon:
                if p in header_lower:
                    lon_idx = header_lower.index(p)
                    break
            for p in possible_alt:
                if p in header_lower:
                    alt_idx = header_lower.index(p)
                    break

            if ts_idx == -1 or lat_idx == -1 or lon_idx == -1:
                print("[警告] 未能完全通过表头识别列，将尝试猜测 (0=时间戳, 3=纬度, 2=经度)。请检查！")
                ts_idx, lat_idx, lon_idx = 0, 3, 2
                alt_idx = 4 if len(header) > 4 else -1
            else:
                print("  > 成功通过表头解析列。")

            print(
                f"  > 使用索引: 时间戳={ts_idx}, 纬度={lat_idx}, 经度={lon_idx}, 高度={alt_idx if alt_idx != -1 else 'N/A'}"
            )

            for i, row in enumerate(reader, start=2):
                if not row or len(row) <= max(ts_idx, lat_idx, lon_idx):
                    print(f"  > [警告] 跳过第 {i} 行 (列数不足或为空): {row}")
                    continue
                try:
                    timestamp_val = row[ts_idx].strip()
                    if timestamp_val.replace('.', '', 1).isdigit():
                        timestamp = datetime.fromtimestamp(
                            float(timestamp_val))  # <--- 使用本地时间
                    else:
                        timestamp = datetime.strptime(
                            timestamp_val, '%Y-%m-%d %H:%M:%S')  # <--- 假设本地时间

                    lat = float(row[lat_idx].strip())
                    lon = float(row[lon_idx].strip())
                    alt = float(row[alt_idx].strip()
                                ) if alt_idx != -1 and alt_idx < len(
                                    row) and row[alt_idx] else 0.0

                    gps_data.append({
                        'time': timestamp,
                        'lat': lat,
                        'lon': lon,
                        'alt': alt
                    })
                except (ValueError, IndexError, TypeError) as e:
                    print(f"  > [警告] 跳过第 {i} 行 {row}: {e}")

            gps_data.sort(key=lambda x: x['time'])
            print(f"成功加载并排序 {len(gps_data)} 条 GPS 记录。")
            return gps_data

    except FileNotFoundError:
        print(f"[错误] GPS 数据文件 '{csv_path}' 未找到。")
        return None
    except Exception as e:
        print(f"[错误] 读取 GPS 数据文件时发生意外错误: {e}")
        return None


def find_closest_gps(image_dt, gps_log, max_tolerance_seconds):
    """在 GPS 记录中查找最接近的时间点 (使用二分查找)"""
    if not image_dt or not gps_log:
        return None

    gps_times = [entry['time'] for entry in gps_log]
    idx = bisect.bisect_left(gps_times, image_dt)
    max_diff_allowed = timedelta(seconds=max_tolerance_seconds)

    candidates = []
    if idx > 0:
        candidates.append(gps_log[idx - 1])
    if idx < len(gps_log):
        candidates.append(gps_log[idx])

    closest_gps = None
    min_diff = max_diff_allowed + timedelta(seconds=1)

    for gps_point in candidates:
        diff = abs(image_dt - gps_point['time'])
        if diff < min_diff:
            min_diff = diff
            closest_gps = gps_point

    if closest_gps and min_diff <= max_diff_allowed:
        return closest_gps
    else:
        return None


# ============================================
# == 单个图片处理逻辑 (用于多进程)
# ============================================

def process_single_image(image_path, gps_log, overwrite_gps, time_tolerance, show_coords, move_nogps, nogps_folder_path):
    filename = os.path.basename(image_path)
    exif_data = get_exif_data(image_path)
    gps_info_current = get_gps_info(exif_data)
    has_gps = gps_info_current is not None
    added_gps = False
    moved_file = False

    status_line = f"{filename}: "

    # 尝试添加/覆盖 GPS
    if gps_log and (not has_gps or overwrite_gps):
        img_time = get_image_datetime(exif_data)
        if img_time:
            closest_data = find_closest_gps(img_time, gps_log, time_tolerance)
            if closest_data:
                if add_gps_to_image(image_path, closest_data['lat'],
                                    closest_data['lon'],
                                    closest_data['alt'],
                                    closest_data['time']): # <--- 传递时间
                    added_gps = True
                    # 重新获取EXIF以反映更改
                    exif_data = get_exif_data(image_path)
                    gps_info_current = get_gps_info(exif_data)
                    has_gps = True # 更新has_gps状态
                else:
                    status_line += "[添加失败]"
            elif not has_gps: # 只有在原本就没有GPS，且找不到匹配时才标记
                status_line += f"[无匹配GPS ({img_time.strftime('%H:%M:%S')})]"
        elif not has_gps: # 只有在原本就没有GPS，且没有拍摄时间时才标记
            status_line += "[无拍摄时间]"

    # 最终状态判断与处理
    if has_gps and gps_info_current:
        status_line += "包含 GPS"
        if show_coords:
            lat, lon = convert_gps_to_decimal(gps_info_current)
            if lat is not None and lon is not None:
                status_line += f" ({lat:.6f}, {lon:.6f})"
            else:
                status_line += " (坐标解析失败)"
    else:
        if not any(x in status_line for x in ["[", "失败"]): # 避免重复添加状态
            status_line += "无 GPS 信息"

        if move_nogps and nogps_folder_path:
            dest_path = os.path.join(nogps_folder_path, filename)
            try:
                # 在移动前确保目标文件夹存在 (多进程中可能需要再次检查)
                os.makedirs(nogps_folder_path, exist_ok=True)
                os.rename(image_path, dest_path)
                status_line += " -> 已移动"
                moved_file = True
            except Exception as e:
                # 注意：在多进程中，print可能不会按预期顺序显示，或者需要特殊处理
                # 对于简单脚本，暂时保留，但大型应用可能需要日志队列
                # print(f"\n[错误] 移动 {filename} 时出错: {e}")
                status_line += f" -> 移动失败 ({e})"

    return {'filename': filename, 'status': status_line.strip(), 'has_gps': has_gps, 'added': added_gps, 'moved': moved_file}


# ============================================
# == 主扫描与处理逻辑
# ============================================


def scan_images(folder_path, show_coords, output_file_path, move_nogps,
                gps_csv_path, overwrite_gps, time_tolerance, num_workers=None):
    """主函数：扫描、检查并处理图片"""

    print("\n" + "=" * 40)
    print("      图片 GPS 信息处理开始")
    print("=" * 40)
    print(f"扫描文件夹: {folder_path}")

    gps_log = None
    if gps_csv_path:
        gps_log = load_gps_csv(gps_csv_path)
        if not gps_log:
            print("[警告] 无法加载 GPS 数据，将仅执行检查和移动操作。")

    image_files = [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
        and f.lower().endswith(SUPPORTED_EXTENSIONS)
    ]

    total = len(image_files)
    if total == 0:
        print("未找到支持的图片文件。")
        return

    print(f"找到 {total} 张图片，开始处理...")

    # 如果 num_workers 未指定，则使用 CPU 核心数，至少为1
    effective_num_workers = num_workers if num_workers is not None else (os.cpu_count() or 1)
    print(f"使用 {effective_num_workers} 个工作进程进行处理...")

    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=effective_num_workers) as executor:
        futures = {
            executor.submit(process_single_image, os.path.join(folder_path, filename),
                            gps_log, overwrite_gps, time_tolerance, show_coords, move_nogps,
                            os.path.join(folder_path, "_nogps_") if move_nogps else None):
            filename
            for filename in image_files
        }
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            filename = futures[future]
            progress = f"处理中: {i + 1}/{total} - {filename:<35}"
            print(f"\r{progress}", end="", flush=True) # 使用 \r 实现行内更新
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"\n[错误] 处理 {filename} 时发生意外: {e}")
                results.append({'filename': filename, 'status': '[处理失败]', 'has_gps': False, 'added': False, 'moved': False})

    count_gps = sum(1 for r in results if r['has_gps'])
    count_added = sum(1 for r in results if r['added'])
    count_moved = sum(1 for r in results if r['moved'])
    output_lines = [r['status'] for r in results]
    # 统一计算最终的无 GPS 数量
    count_nogps_final = total - count_gps

    print("\n" + "=" * 40)
    print("      处理完成！")
    print("=" * 40)
    print(f"总图片数:     {total}")
    print(f"有 GPS 图片:  {count_gps}")
    print(f"无 GPS 图片:  {count_nogps_final}")
    if gps_log:
        print(f"成功添加 GPS: {count_added}")
    if move_nogps:
        print(f"成功移动图片: {count_moved}")

    if output_file_path:
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(
                    f"处理报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"扫描文件夹: {folder_path}\n")
                f.write("-" * 30 + "\n")
                for line in output_lines:
                    f.write(line + '\n')
                f.write("-" * 30 + "\n")
                f.write(
                    f"总结: 总计={total}, 有GPS={count_gps}, 无GPS={count_nogps_final}, 添加={count_added}, 移动={count_moved}\n"
                )
            print(f"结果已保存到: {output_file_path}")
        except Exception as e:
            print(f"[错误] 保存结果文件时出错: {e}")


# ============================================
# == 命令行参数与交互模式
# ============================================


def setup_arg_parser():
    parser = argparse.ArgumentParser(
        description="图片 GPS 信息扫描与补充工具。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
示例:
  # 仅扫描并显示坐标
  python gps_tool.py /path/to/images -c

  # 扫描，从 CSV 补充 GPS (容差 300s)，并移动无 GPS 文件
  python gps_tool.py /path/to/images -m -g gps_log.csv -t 300

  # 扫描，强制用 CSV 覆盖所有 GPS，并输出报告
  python gps_tool.py /path/to/images -g gps_log.csv --overwrite -o report.txt
""")
    parser.add_argument("folder", help="要扫描的图片文件夹路径。")
    parser.add_argument("-c",
                        "--coordinates",
                        action="store_true",
                        help="显示找到的 GPS 坐标 (十进制格式)。")
    parser.add_argument("-m",
                        "--move",
                        action="store_true",
                        help="将最终没有 GPS 信息的图片移动到 '_nogps_' 子文件夹。")
    parser.add_argument("-o", "--output", help="将详细处理结果输出到指定的文本文件。")
    parser.add_argument("-g",
                        "--gps-file",
                        help="""包含 GPS 数据的 CSV 文件路径。
要求: 包含表头，能识别 'timestamp'/'time'/'datatime', 
      'latitude'/'lat', 'longitude'/'lon'。时间可以是 
      Unix 时间戳或 'YYYY-MM-DD HH:MM:SS' 格式。""")
    parser.add_argument("--overwrite",
                        action="store_true",
                        help="如果图片已有 GPS 信息，也尝试用 CSV 数据覆盖它。")
    parser.add_argument(
        "-t",
        "--tolerance",
        type=int,
        default=DEFAULT_TOLERANCE_SECONDS,
        help=f"时间匹配的最大容差 (秒)。默认为 {DEFAULT_TOLERANCE_SECONDS} 秒。")
    parser.add_argument("-v",
                        "--version",
                        action="version",
                        version="%(prog)s 1.6")
    parser.add_argument("--workers",
                        type=int,
                        default=None,
                        help="用于处理图片的工作进程数 (默认: 自动确定, 通常为CPU核心数)。",
                        metavar="N")
    return parser


def run_interactive_mode():
    print("\n欢迎使用图片 GPS 信息处理工具 (交互模式)")
    print("=" * 40)

    folder_path = input("1. 请输入要扫描的图片文件夹路径: ").strip()
    if not (folder_path and os.path.exists(folder_path)
            and os.path.isdir(folder_path)):
        print("[错误] 无效的文件夹路径。程序退出。")
        sys.exit(1)

    show_coords = input("2. 是否显示具体坐标？ (y/n, 默认 n): ").strip().lower() == 'y'
    move_files = input("3. 是否移动无 GPS 图片？ (y/n, 默认 n): ").strip().lower() == 'y'
    output_file = input("4. 输出结果到文件？ (输入路径或留空): ").strip() or None

    gps_csv_path = input("5. 输入 GPS 数据文件路径？ (输入路径或留空): ").strip() or None
    overwrite_gps = False
    time_tolerance = DEFAULT_TOLERANCE_SECONDS

    if gps_csv_path:
        if not os.path.exists(gps_csv_path):
            print(f"[错误] GPS 文件 '{gps_csv_path}' 不存在。程序退出。")
            sys.exit(1)
        overwrite_gps = input(
            "   - 是否覆盖已有 GPS？ (y/n, 默认 n): ").strip().lower() == 'y'
        try:
            tolerance_input = input(
                f"   - 输入最大时间容差 (秒，默认 {DEFAULT_TOLERANCE_SECONDS}): ").strip()
            time_tolerance = int(
                tolerance_input
            ) if tolerance_input else DEFAULT_TOLERANCE_SECONDS
        except ValueError:
            print(f"   - [警告] 无效输入，将使用默认容差 {DEFAULT_TOLERANCE_SECONDS} 秒。")

    num_workers_str = input(f"6. 输入处理工作进程数 (可选, 默认将使用CPU核心数): ").strip()
    num_workers = None
    if num_workers_str:
        try:
            num_workers = int(num_workers_str)
            if num_workers <= 0:
                print("   - [警告] 工作进程数必须为正整数，将使用默认值。")
                num_workers = None
        except ValueError:
            print("   - [警告] 无效的工作进程数输入，将使用默认值。")
            num_workers = None

    return {
        "folder": folder_path,
        "coordinates": show_coords,
        "output": output_file,
        "move": move_files,
        "gps_file": gps_csv_path,
        "overwrite": overwrite_gps,
        "tolerance": time_tolerance,
        "workers": num_workers,
    }


# ============================================
# == 程序主入口
# ============================================


def main():
    parser = setup_arg_parser()

    if len(sys.argv) == 1:
        try:
            params = run_interactive_mode()
            args = argparse.Namespace(**params)
        except (KeyboardInterrupt, EOFError):
            print("\n用户中断，程序退出。")
            sys.exit(0)
    else:
        args = parser.parse_args()

    if not os.path.exists(args.folder) or not os.path.isdir(args.folder):
        print(f"[错误] 文件夹 '{args.folder}' 不存在或无效。")
        sys.exit(1)
    if args.gps_file and not os.path.exists(args.gps_file):
        print(f"[错误] GPS 数据文件 '{args.gps_file}' 不存在。")
        sys.exit(1)

    try:
        scan_images(args.folder, args.coordinates, args.output, args.move,
                    args.gps_file, args.overwrite, args.tolerance, args.workers)
    except KeyboardInterrupt:
        print("\n\n[信息] 处理被用户中断。")
    except Exception as e:
        print(f"\n[严重错误] 处理过程中发生意外: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n程序执行完毕。")


if __name__ == "__main__":
    main()
