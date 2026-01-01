#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
检查特定图片的GPS信息
"""

import sys
import os
from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS
import piexif

def get_exif_data(image_path):
    """提取图片的EXIF数据"""
    try:
        with Image.open(image_path) as image:
            image.load()  # 确保图片数据已加载

            # 优先尝试从 image.info['exif'] 获取原始 EXIF 数据 (bytes)
            raw_exif_bytes = image.info.get('exif')
            if raw_exif_bytes:
                try:
                    # piexif.load() 将 bytes 解析为标准的 EXIF 字典结构
                    return piexif.load(raw_exif_bytes)
                except Exception as e: 
                    print(f"piexif解析失败: {e}")
                    # 如果piexif解析失败，尝试Pillow的内部方法
                    pass 

            # 如果 image.info['exif'] 不可用或解析失败，尝试 Pillow 自带的 _getexif()
            if hasattr(image, '_getexif'):
                pil_exif_data = image._getexif() # Pillow 的 EXIF 解析结果
                if pil_exif_data:
                    return pil_exif_data # 直接返回这个字典

            return None # 如果两种方法都没有获取到 EXIF 数据
    except Exception as e:
        print(f"读取图片 {os.path.basename(image_path)} 的 EXIF 数据时出错: {e}")
        return None

def get_gps_info(exif_data):
    """从 EXIF 数据中提取 GPS 信息字典"""
    if not exif_data:
        return None
    
    gps_ifd_data = None

    # 检查是否是 piexif.load() 的输出格式 (包含 'GPS' key)
    if 'GPS' in exif_data and isinstance(exif_data['GPS'], dict):
        gps_ifd_data = exif_data['GPS']
        print("从piexif格式中找到GPS数据")
    # 检查是否是 Pillow 的 _getexif() 输出格式 (包含 GPSInfo tag)
    elif isinstance(exif_data, dict): 
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            if tag_name == 'GPSInfo' and isinstance(value, dict):
                gps_ifd_data = value
                print("从Pillow格式中找到GPS数据")
                break
    
    if gps_ifd_data:
        gps_info_dict = {}
        for gps_tag_id, gps_value in gps_ifd_data.items():
            gps_tag_name = GPSTAGS.get(gps_tag_id, gps_tag_id)
            gps_info_dict[gps_tag_name] = gps_value
        
        # 检查GPS字典是否包含必要的坐标数据
        required_tags = ['GPSLatitude', 'GPSLatitudeRef', 'GPSLongitude', 'GPSLongitudeRef']
        has_all_required = all(tag in gps_info_dict for tag in required_tags)
        
        if not has_all_required:
            print("警告: GPS字典不包含完整的坐标数据 (缺少经纬度或参考方向)")
            print(f"缺少的必要标签: {[tag for tag in required_tags if tag not in gps_info_dict]}")
            return None
            
        return gps_info_dict if gps_info_dict else None # 如果字典为空返回None
        
    return None

def _convert_to_degrees(value):
    """将 GPS 元组 (度, 分, 秒) 转换为十进制"""
    try:
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise TypeError(f"GPS值不是包含3个元素的元组/列表: {value}")
        first_element = value[0]
        if isinstance(first_element, (tuple, list)) and len(first_element) == 2:
            if not (isinstance(value[1], (tuple, list)) and len(value[1]) == 2
                    and isinstance(value[2], (tuple, list)) and len(value[2]) == 2):
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
        elif hasattr(first_element, 'numerator') and hasattr(first_element, 'denominator'):
            d = float(first_element.numerator) / float(first_element.denominator)
            m = float(value[1].numerator) / float(value[1].denominator)
            s = float(value[2].numerator) / float(value[2].denominator)
        else:
            raise TypeError(f"未知的 GPS 值格式或结构: {value}")
        return d + (m / 60.0) + (s / 3600.0)
    except (TypeError, ZeroDivisionError, IndexError, AttributeError) as e:
        print(f"转换度数时出错: {value} - {e}")
        return None

def convert_gps_to_decimal(gps_info):
    """将 EXIF GPS 信息转换为十进制经纬度"""
    lat = None
    lon = None
    gps_latitude = gps_info.get('GPSLatitude')
    gps_latitude_ref = gps_info.get('GPSLatitudeRef')
    gps_longitude = gps_info.get('GPSLongitude')
    gps_longitude_ref = gps_info.get('GPSLongitudeRef')
    
    print(f"GPS数据详情:")
    print(f"  纬度数据: {gps_latitude}")
    print(f"  纬度参考: {gps_latitude_ref}")
    print(f"  经度数据: {gps_longitude}")
    print(f"  经度参考: {gps_longitude_ref}")
    
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

def main():
    if len(sys.argv) != 2:
        print(f"用法: {sys.argv[0]} <图片路径>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    if not os.path.exists(image_path):
        print(f"错误: 文件 '{image_path}' 不存在")
        sys.exit(1)
        
    print(f"检查图片: {image_path}")
    
    # 获取EXIF数据
    exif_data = get_exif_data(image_path)
    if not exif_data:
        print("未找到EXIF数据")
        sys.exit(1)
        
    # 打印EXIF数据结构
    if isinstance(exif_data, dict):
        if 'GPS' in exif_data:
            print("EXIF数据包含GPS字段")
            print(f"GPS字段内容类型: {type(exif_data['GPS'])}")
            print(f"GPS字段内容: {exif_data['GPS']}")
        else:
            print("EXIF数据不包含GPS字段")
            # 检查是否有GPSInfo标签
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == 'GPSInfo':
                    print(f"找到GPSInfo标签 (ID: {tag_id})")
                    print(f"GPSInfo内容类型: {type(value)}")
                    print(f"GPSInfo内容: {value}")
                    break
    
    # 获取GPS信息
    gps_info = get_gps_info(exif_data)
    if gps_info:
        print("\n找到GPS信息:")
        for key, value in gps_info.items():
            print(f"  {key}: {value}")
            
        # 转换为十进制坐标
        lat, lon = convert_gps_to_decimal(gps_info)
        if lat is not None and lon is not None:
            print(f"\n十进制坐标: ({lat:.6f}, {lon:.6f})")
        else:
            print("\n无法转换为十进制坐标")
    else:
        print("\n未找到有效的GPS信息")

if __name__ == "__main__":
    main()