#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天记录发言次数统计脚本
统计5-11月大大AA群聊的发言次数,按wxid聚合
"""

import requests
import re
import json
import argparse
from collections import defaultdict
from datetime import datetime


class ChatStatistics:
    def __init__(self, talker="大大AA", base_url="http://192.168.6.192:5030/api/v1/chatlog"):
        self.base_url = base_url
        self.talker = talker
        # 存储统计结果: {wxid: {"name": 昵称, "count": 次数, "names": {昵称集合}}}
        self.stats = defaultdict(lambda: {"name": "", "count": 0, "names": set()})
        
    def build_url(self, year, month):
        """构建请求URL"""
        time_range = f"{year}-{month:02d}~{year}-{month:02d}"
        return f"{self.base_url}?time={time_range}&talker={self.talker}"
    
    def parse_message_records(self, text_content):
        """
        解析消息记录
        格式: 发言者名字(wxid) 日期 时间\n消息内容
        返回: [(wxid, name, content), ...]
        """
        # 匹配模式: 名字(wxid) 日期 时间
        # 例如: 南瓜nagra(wxid_kn9jl7gvha8o42) 06-01 09:34:40
        # 使用 ^ 锚定行首, [^\n(]+ 避免匹配换行符, [ \t]+ 避免匹配换行符
        pattern = r'^([^\n(]+)\(([^)\n]+)\)[ \t]+\d{2}-\d{2}[ \t]+\d{2}:\d{2}:\d{2}'
        
        results = []
        matches = list(re.finditer(pattern, text_content, flags=re.MULTILINE))
        
        for i, match in enumerate(matches):
            name = match.group(1)
            wxid = match.group(2)
            
            # 获取消息内容 (当前匹配结束到下一个匹配开始, 或者到文本结束)
            start_pos = match.end()
            end_pos = matches[i+1].start() if i < len(matches) - 1 else len(text_content)
            content = text_content[start_pos:end_pos].strip()
            
            results.append((wxid.strip(), name.strip(), content))
            
        return results
    
    def fetch_month_data(self, year, month):
        """获取某月的聊天数据"""
        url = self.build_url(year, month)
        print(f"正在请求 {year}年{month}月 数据...")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # API返回的是纯文本,不是JSON
            text_content = response.text
            
            # 直接解析文本内容
            message_count = 0
            records = self.parse_message_records(text_content)
            for wxid, name, content in records:
                # 清理昵称: 使用正则去除开头的 > 和空白字符
                clean_name = re.sub(r'^[\s>]+', '', name).strip()
                
                # 过滤无效昵称 (如果清理后为空, 或者包含换行符)
                if not clean_name or "\n" in clean_name:
                    continue
                
                self.stats[wxid]["count"] += 1
                self.stats[wxid]["names"].add(clean_name)
                # 使用最新的昵称
                self.stats[wxid]["name"] = clean_name
                message_count += 1
            
            print(f"  {year}年{month}月: 解析到 {message_count} 条发言")
            return message_count
            
        except requests.exceptions.RequestException as e:
            print(f"  请求失败: {e}")
            return 0
        except Exception as e:
            print(f"  处理失败: {e}")
            return 0
    
    def collect_all_months(self, year=2025, start_month=5, end_month=11):
        """收集指定月份范围的数据"""
        print(f"\n开始统计 {year}年 {start_month}-{end_month}月 大大AA群聊发言次数\n")
        print("="*60)
        
        total_messages = 0
        for month in range(start_month, end_month + 1):
            count = self.fetch_month_data(year, month)
            total_messages += count
        
        print("="*60)
        print(f"\n总计解析到 {total_messages} 条发言记录")
        print(f"发言人数: {len(self.stats)} 人\n")
    
    def generate_report(self, output_file="chat_statistics.json"):
        """生成统计报告"""
        # 转换为可序列化的格式
        report = []
        for wxid, info in self.stats.items():
            report.append({
                "wxid": wxid,
                "name": info["name"],
                "all_names": sorted(list(info["names"])),  # 所有使用过的昵称
                "count": info["count"]
            })
        
        # 按发言次数降序排序
        report.sort(key=lambda x: x["count"], reverse=True)
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        import os
        print(f"统计结果已保存到: {os.path.abspath(output_file)}\n")
        return report
    
    def generate_markdown_report(self, output_file="result.md"):
        """生成完整的markdown统计报告"""
        sorted_stats = sorted(
            self.stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        total_count = sum(info["count"] for _, info in sorted_stats)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 大大AA群聊 发言次数统计报告\n\n")
            f.write(f"**统计时间范围**: 2025年5月 - 2025年11月\n\n")
            f.write(f"**总发言人数**: {len(sorted_stats)} 人\n\n")
            f.write(f"**总发言次数**: {total_count} 次\n\n")
            f.write("---\n\n")
            f.write("## 完整统计列表\n\n")
            f.write("| 排名 | 昵称 | wxid | 发言次数 | 曾用昵称 |\n")
            f.write("|------|------|------|----------|----------|\n")
            
            for i, (wxid, info) in enumerate(sorted_stats, 1):
                name = info["name"]
                count = info["count"]
                all_names = ", ".join(sorted(list(info["names"])))
                f.write(f"| {i} | {name} | `{wxid}` | {count} | {all_names} |\n")
            
            f.write("\n---\n\n")
            f.write(f"*统计生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        import os
        print(f"\n完整统计报告已保存到: {os.path.abspath(output_file)}")
    
    def print_top_speakers(self, top_n=20):
        """打印发言最多的前N名"""
        sorted_stats = sorted(
            self.stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        print("="*60)
        print(f"发言次数 TOP {top_n}")
        print("="*60)
        print(f"{'排名':<6}{'昵称':<20}{'发言次数':<10}{'wxid':<30}")
        print("-"*60)
        
        for i, (wxid, info) in enumerate(sorted_stats[:top_n], 1):
            name = info["name"]
            count = info["count"]
            # 如果有多个昵称,显示提示
            name_suffix = f" ({len(info['names'])}个昵称)" if len(info["names"]) > 1 else ""
            print(f"{i:<6}{name:<20}{count:<10}{wxid:<30}{name_suffix}")
        
        print("="*60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="微信群聊发言次数统计脚本")
    
    parser.add_argument("--year", type=int, default=2025, help="统计年份 (默认: 2025)")
    parser.add_argument("--start-month", type=int, default=5, help="开始月份 (默认: 5)")
    parser.add_argument("--end-month", type=int, default=11, help="结束月份 (默认: 11)")
    parser.add_argument("--talker", type=str, default="大大AA", help="群聊名称 (默认: 大大AA)")
    parser.add_argument("--base-url", type=str, default="http://192.168.6.192:5030/api/v1/chatlog", help="API基础URL")
    parser.add_argument("--top-n", type=int, default=20, help="显示排名前N位 (默认: 20)")
    
    args = parser.parse_args()
    
    # 创建统计对象
    stats = ChatStatistics(talker=args.talker, base_url=args.base_url)
    
    # 收集数据
    stats.collect_all_months(year=args.year, start_month=args.start_month, end_month=args.end_month)
    
    # 生成报告
    report = stats.generate_report()
    
    # 生成markdown完整报告
    stats.generate_markdown_report()
    
    # 打印前N名
    stats.print_top_speakers(top_n=args.top_n)
    
    print(f"\n✅ 统计完成!")
    print(f"   总发言人数: {len(report)} 人")
    print(f"   总发言次数: {sum(item['count'] for item in report)} 次")
    print(f"   JSON结果: chat_statistics.json")
    print(f"   完整报告: result.md")


if __name__ == "__main__":
    main()
