import os
import logging
import argparse
from datetime import datetime
import collections
import math
import json

import numpy as np
from PIL import Image
import pillow_heif
import exifread
import reverse_geocoder as rg
from geopy.distance import geodesic
from tqdm import tqdm

# 配置支持 HEIC
pillow_heif.register_heif_opener()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("photo_report.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FileScanner:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.image_exts = {'.jpg', '.jpeg', '.png', '.heic'}
        self.video_exts = {'.mp4', '.mov', '.avi', '.mkv'}

    def scan(self):
        images = []
        videos = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                full_path = os.path.join(root, file)
                if ext in self.image_exts:
                    images.append(full_path)
                elif ext in self.video_exts:
                    videos.append(full_path)
        return images, videos

class ExifExtractor:
    @staticmethod
    def _convert_to_degrees(value):
        """将 EXIF 坐标转换为十进制角度"""
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def get_exif_data(file_path):
        data = {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'size': os.path.getsize(file_path),
            'datetime': None,
            'lat': None,
            'lon': None,
            'alt': None,
            'make': None,
            'model': None,
            'lens': None,
            'focal_length': None,
            'aperture': None,
            'exposure_time': None,
            'iso': None,
            'is_image': True
        }

        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)

            # 时间
            dt_str = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
            if dt_str:
                try:
                    data['datetime'] = datetime.strptime(str(dt_str), '%Y:%m:%d %H:%M:%S')
                except ValueError:
                    pass

            # GPS
            lat = tags.get('GPS GPSLatitude')
            lat_ref = tags.get('GPS GPSLatitudeRef')
            lon = tags.get('GPS GPSLongitude')
            lon_ref = tags.get('GPS GPSLongitudeRef')
            if lat and lat_ref and lon and lon_ref:
                data['lat'] = ExifExtractor._convert_to_degrees(lat)
                if lat_ref.values[0] != 'N':
                    data['lat'] = -data['lat']
                data['lon'] = ExifExtractor._convert_to_degrees(lon)
                if lon_ref.values[0] != 'E':
                    data['lon'] = -data['lon']

            alt = tags.get('GPS GPSAltitude')
            if alt:
                data['alt'] = float(alt.values[0].num) / float(alt.values[0].den)

            # 设备与参数
            data['make'] = str(tags.get('Image Make', 'Unknown')).strip()
            data['model'] = str(tags.get('Image Model', 'Unknown')).strip()
            data['lens'] = str(tags.get('EXIF LensModel', 'Unknown')).strip()
            
            focal = tags.get('EXIF FocalLength')
            if focal:
                data['focal_length'] = float(focal.values[0].num) / float(focal.values[0].den)
            
            aperture = tags.get('EXIF FNumber')
            if aperture:
                data['aperture'] = float(aperture.values[0].num) / float(aperture.values[0].den)
            
            exposure = tags.get('EXIF ExposureTime')
            if exposure:
                data['exposure_time'] = f"{exposure.values[0].num}/{exposure.values[0].den}"
            
            iso = tags.get('EXIF ISOSpeedRatings')
            if iso:
                data['iso'] = int(iso.values[0])

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
        
        return data

class DataAnalyzer:
    def __init__(self, images_data, videos_data):
        self.images = [d for d in images_data if d['datetime']]
        self.all_images = images_data
        self.videos = videos_data
        self.results = {}

    def analyze(self):
        self._analyze_overview()
        self._analyze_space()
        self._analyze_time()
        self._analyze_tech()
        return self.results

    def _analyze_overview(self):
        def get_safe_size(path):
            try:
                if os.path.exists(path):
                    return os.path.getsize(path)
            except Exception as e:
                logger.warning(f"Could not get size for {path}: {e}")
            return 0

        img_size = sum(d.get('size', 0) for d in self.all_images)
        vid_size = sum(get_safe_size(p) for p in self.videos)
        total_size = img_size + vid_size
        
        self.results['overview'] = {
            'total_files': len(self.all_images) + len(self.videos),
            'image_count': len(self.all_images),
            'video_count': len(self.videos),
            'total_size_gb': total_size / (1024**3)
        }

    def _analyze_space(self):
        coords_data = [d for d in self.images if d['lat'] is not None]
        if not coords_data:
            self.results['space'] = None
            return

        # 城市反编码
        coords = [(d['lat'], d['lon']) for d in coords_data]
        locations = rg.search(coords)
        city_counts = collections.Counter([loc['name'] for loc in locations])
        
        # 海拔
        alts_data = [d for d in self.images if d['alt'] is not None]
        max_alt_d = max(alts_data, key=lambda x: x['alt']) if alts_data else None
        
        # 地理极值
        north_d = max(coords_data, key=lambda x: x['lat'])
        south_d = min(coords_data, key=lambda x: x['lat'])
        east_d = max(coords_data, key=lambda x: x['lon'])
        west_d = min(coords_data, key=lambda x: x['lon'])

        # 轨迹距离
        sorted_images = sorted(self.images, key=lambda x: x['datetime'])
        distance = 0
        last_coord = None
        for d in sorted_images:
            if d['lat'] is not None:
                curr_coord = (d['lat'], d['lon'])
                if last_coord:
                    distance += geodesic(last_coord, curr_coord).km
                last_coord = curr_coord

        self.results['space'] = {
            'cities': city_counts.most_common(10),
            'max_alt': max_alt_d['alt'] if max_alt_d else 0,
            'max_alt_path': max_alt_d['path'] if max_alt_d else None,
            'total_distance_km': distance,
            'bounds': {
                'north': {'val': north_d['lat'], 'path': north_d['path']},
                'south': {'val': south_d['lat'], 'path': south_d['path']},
                'east': {'val': east_d['lon'], 'path': east_d['path']},
                'west': {'val': west_d['lon'], 'path': west_d['path']}
            }
        }

    def _analyze_time(self):
        if not self.images:
            self.results['time'] = None
            return

        hours = [d['datetime'].hour for d in self.images]
        hour_counts = collections.Counter(hours)
        
        # 黄金时刻 (粗略估算: 6-8, 17-19)
        golden_hour_count = sum(1 for h in hours if h in [6, 7, 17, 18])
        
        # 深夜 (22-5)
        night_count = sum(1 for h in hours if h >= 22 or h <= 5)
        
        # 最忙碌的一天
        dates = [d['datetime'].date() for d in self.images]
        date_counts = collections.Counter(dates)
        busy_day, busy_count = date_counts.most_common(1)[0]

        # 作息极值 (最早/最晚拍摄的一张)
        earliest_d = min(self.images, key=lambda x: x['datetime'].time())
        latest_d = max(self.images, key=lambda x: x['datetime'].time())

        self.results['time'] = {
            'golden_hour_ratio': golden_hour_count / len(self.images),
            'night_count': night_count,
            'busy_day': busy_day,
            'busy_count': busy_count,
            'hour_distribution': hour_counts,
            'earliest': {'time': earliest_d['datetime'].strftime('%H:%M:%S'), 'path': earliest_d['path']},
            'latest': {'time': latest_d['datetime'].strftime('%H:%M:%S'), 'path': latest_d['path']}
        }

    def _analyze_tech(self):
        if not self.images:
            self.results['tech'] = None
            return

        makes = collections.Counter([d['make'] for d in self.images if d['make']])
        models = collections.Counter([d['model'] for d in self.images if d['model']])
        lenses = collections.Counter([d['lens'] for d in self.images if d['lens'] and d['lens'] != 'Unknown'])
        focals = collections.Counter([round(d['focal_length']) for d in self.images if d['focal_length']])
        
        iso_val = [d['iso'] for d in self.images if d['iso']]

        # 手机 vs 相机分类
        phone_brands = {'apple', 'samsung', 'google', 'xiaomi', 'huawei', 'oppo', 'vivo', 'meizu', 'oneplus'}
        mobile_count = 0
        camera_count = 0
        for d in self.images:
            make = str(d.get('make', '')).lower()
            if any(brand in make for brand in phone_brands):
                mobile_count += 1
            elif make:
                camera_count += 1

        self.results['tech'] = {
            'top_makes': makes.most_common(5),
            'top_models': models.most_common(5),
            'top_lenses': lenses.most_common(5),
            'focal_distribution': focals.most_common(10),
            'max_iso': max(iso_val) if iso_val else 0,
            'device_dist': {
                'mobile': mobile_count,
                'camera': camera_count,
                'total': len(self.images)
            }
        }

class ReportGenerator:
    def __init__(self, data):
        self.data = data

    def generate(self):
        overview = self.data['overview']
        space = self.data['space']
        time = self.data['time']
        tech = self.data['tech']

        report = [
            f"# 📷 年度摄影技术报告",
            f"\n> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"## 📊 概览统计",
            f"- **总文件数**：{overview['total_files']}",
            f"- **照片数量**：{overview['image_count']}",
            f"- **视频数量**：{overview['video_count']}",
            f"- **总占用空间**：{overview['total_size_gb']:.2f} GB",
        ]

        if space:
            bounds = space['bounds']
            report.extend([
                f"\n## 🌍 空间维度：足迹与远方",
                f"- **点亮城市**：{', '.join([f'{c[0]}({c[1]})' for c in space['cities']])}",
                f"- **影像总里程**：{space['total_distance_km']:.2f} km",
                f"- **海拔之巅**：{space['max_alt']:.1f} m",
                f"  - 📍 对应照片：`{space['max_alt_path']}`",
                f"- **地理极值**：",
                f"  - ⬆️ 北至：{bounds['north']['val']:.4f} (`{bounds['north']['path']}`)",
                f"  - ⬇️ 南至：{bounds['south']['val']:.4f} (`{bounds['south']['path']}`)",
                f"  - ➡️ 东至：{bounds['east']['val']:.4f} (`{bounds['east']['path']}`)",
                f"  - ⬅️ 西至：{bounds['west']['val']:.4f} (`{bounds['west']['path']}`)",
            ])

        if time:
            report.extend([
                f"\n## 🕒 时间维度：生活的脉搏",
                f"- **最忙碌的一天**：{time['busy_day']} (快门次数: {time['busy_count']})",
                f"- **作息极值**：",
                f"  - 🌅 拍摄时间最早：{time['earliest']['time']} (`{time['earliest']['path']}`)",
                f"  - 🌙 拍摄时间最晚：{time['latest']['time']} (`{time['latest']['path']}`)",
                f"- **黄金时刻比例**：{time['golden_hour_ratio']*100:.1f}%",
                f"- **深夜/凌晨记录**：{time['night_count']} 次拍摄",
            ])

        if tech:
            dist = tech['device_dist']
            mobile_pct = (dist['mobile'] / dist['total'] * 100) if dist['total'] else 0
            camera_pct = (dist['camera'] / dist['total'] * 100) if dist['total'] else 0
            report.extend([
                f"\n## ⚙️ 技术维度：器材与参数",
                f"- **设备分布**：",
                f"  - 📱 手机拍摄：{dist['mobile']} 张 ({mobile_pct:.1f}%)",
                f"  - 📷 相机拍摄：{dist['camera']} 张 ({camera_pct:.1f}%)",
                f"- **核心器材**：{', '.join([f'{m[0]}({m[1]})' for m in tech['top_models']])}",
                f"- **常用镜头**：{', '.join([f'{l[0]}({l[1]})' for l in tech['top_lenses']])}",
                f"- **常用焦段**：{', '.join([f'{f[0]}mm({f[1]})' for f in tech['focal_distribution']])}",
                f"- **最高 ISO**：{tech['max_iso']}",
            ])

        return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Generate a technical report for your photos.")
    parser.add_argument("input", help="Directory containing photos and videos")
    parser.add_argument("-o", "--output", default="PhotoReport_Generated.md", help="Output Markdown file")
    args = parser.parse_args()

    if not os.path.isdir(args.input):
        logger.error(f"Input directory not found: {args.input}")
        return

    logger.info(f"Scanning directory: {args.input}")
    scanner = FileScanner(args.input)
    images, videos = scanner.scan()
    logger.info(f"Found {len(images)} images and {len(videos)} videos.")

    images_data = []
    logger.info("Extracting EXIF data...")
    for img_path in tqdm(images, desc="Processing Images"):
        images_data.append(ExifExtractor.get_exif_data(img_path))

    logger.info("Analyzing data...")
    analyzer = DataAnalyzer(images_data, videos)
    results = analyzer.analyze()

    logger.info("Generating report...")
    generator = ReportGenerator(results)
    report_content = generator.generate()

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    logger.info(f"Report generated successfully: {args.output}")

if __name__ == "__main__":
    main()
