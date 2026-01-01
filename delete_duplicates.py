import json
import os
import random
import re
import subprocess
import time


def read_file_list(filename="一人.txt"):
    """
    从指定的文本文件中读取文件列表。
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            print(f"成功读取文件 '{filename}'。")
            return f.read()
    except FileNotFoundError:
        print(f"错误：找不到文件 '{filename}'。请确保该文件与脚本在同一个目录下。")
        return None

def find_files_to_delete(file_list_str):
    """
    解析文件列表字符串，找到并返回需要删除的重复文件列表。
    """
    # 用于从每行中提取文件名的正则表达式
    # 这个表达式会匹配 '├──' 后面跟着的任何字符，直到行尾
    filename_pattern = re.compile(r'├──\s*(.+)')
    all_files = []
    for line in file_list_str.strip().split('\n'):
        match = filename_pattern.search(line)
        if match:
            all_files.append(match.group(1).strip())

    # 用于识别重复文件的正则表达式，例如：file(1).pdf 或 file (1).pdf
    duplicate_pattern = re.compile(r'(.+?)\s*\(\d+\)\..+$')
    
    files_to_delete = []
    
    # 筛选出所有符合重复文件模式的文件名
    for f in all_files:
        if duplicate_pattern.match(f):
            files_to_delete.append(f)
            
    return files_to_delete

def delete_files_batch(files_to_delete, auth_token, directory_path):
    """
    使用 curl 命令删除一批文件。
    """
    if not files_to_delete:
        print("这一批次没有需要删除的文件。")
        return

    # 构建 curl 命令
    url = "http://alist.2109116.xyz:21006/api/fs/remove"
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Authorization': auth_token,
        'Content-Type': 'application/json;charset=UTF-8',
    }
    data = {
        "dir": directory_path,
        "names": files_to_delete
    }
    
    # 将 curl 命令构建为一个参数列表
    curl_command = [
        'curl', url,
        '-X', 'POST',
        '--insecure', # 忽略 SSL 证书验证
    ]

    for key, value in headers.items():
        curl_command.extend(['-H', f'{key}: {value}'])
        
    curl_command.extend(['--data-raw', json.dumps(data)])

    print(f"准备删除 {len(files_to_delete)} 个文件...")
    
    try:
        # 执行命令
        # 注意：subprocess.run 会等待命令执行完成
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True, encoding='utf-8')
        print("成功删除批次:", files_to_delete)
        print("服务器响应:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"删除批次失败: {files_to_delete}")
        print("命令执行出错:", e)
        print("错误输出 (Stderr):", e.stderr)

def main():
    """
    主函数，用于协调整个文件删除流程。
    """
    # --- 重要 ---
    # 请将 "YOUR_AUTHORIZATION_TOKEN" 替换为您自己的真实授权令牌
    auth_token = "YOUR_AUTHORIZATION_TOKEN"
    
    # 您网盘上的目标目录
    remote_directory = "/baidu/我的资源/Comic/一人"

    if auth_token == "YOUR_AUTHORIZATION_TOKEN":
        print("错误：请在脚本中将 'YOUR_AUTHORIZATION_TOKEN' 替换为您的真实令牌。")
        return
        
    file_list_data = read_file_list()
    if file_list_data is None:
        return

    files_to_delete = find_files_to_delete(file_list_data)
    
    if not files_to_delete:
        print("没有找到需要删除的重复文件。")
        return

    print(f"共找到 {len(files_to_delete)} 个重复文件需要删除。")
    print("待删除文件列表:", files_to_delete)
    
    # 让用户确认是否继续
    confirm = input("是否确认执行删除操作？ (输入 'yes' 继续): ")
    if confirm.lower() != 'yes':
        print("操作已取消。")
        return

    # 将文件分批处理，每批10个
    batch_size = 10
    for i in range(0, len(files_to_delete), batch_size):
        batch = files_to_delete[i:i + batch_size]
        delete_files_batch(batch, auth_token, remote_directory)
        
        # 如果不是最后一批，就随机暂停一段时间
        if i + batch_size < len(files_to_delete):
            delay = random.uniform(1, 5) # 随机延迟1到5秒
            print(f"等待 {delay:.2f} 秒后执行下一批...")
            time.sleep(delay)

    print("脚本执行完毕。")

if __name__ == "__main__":
    main()