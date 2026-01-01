import os
import json
import requests
from PIL import Image
from io import BytesIO
import urllib.parse
import time
import logging

# 设置日志记录器
logging.basicConfig(filename='error.log', level=logging.ERROR, format='%(asctime)s %(message)s')

def extract_folder_name(path):
    parts = path.strip('/').split('/')
    return parts[-1] if parts else None

def get_subdirectories(base_url, name):
    path_param = f"/{name}"
    query_params = {
        'path': path_param,
        'password': '',
        'orderBy': '',
        'orderDirection': ''
    }
    encoded_query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
    url = f"{base_url}?{encoded_query}"

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'referer': 'https://www.cosersets.com/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    response = requests.get(url, headers=headers, verify=False)
    if response.status_code != 200:
        print("Failed to retrieve data")
        return []

    data = response.json()
    subdirectories = [item['name'] for item in data['data']['files'] if item['type'] == 'FOLDER']
    return subdirectories

def ensure_directory_exists(path):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def download_file(url, local_path, headers):
    try:
        if os.path.exists(local_path):
            print(f"File already exists, skipping: {local_path}")
            return
        ensure_directory_exists(local_path)
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {local_path}")
    except requests.exceptions.SSLError as e:
        logging.error(f"SSL error for file {local_path}: {e}")

def process_directory(url, base_output_folder, headers):
    try:
        response = requests.get(url, headers=headers, verify=False)
        if response.status_code != 200:
            print("Failed to retrieve data")
            return

        data = response.json()
        files = data['data']['files']

        for file in files:
            # print(file)
            try:
                local_path = os.path.join(base_output_folder, file['path'].strip('/'), file['name'])
                if file['type'] == 'FILE':
                    if file['name'].endswith('.webp'):
                        ensure_directory_exists(local_path)
                        image_response = requests.get(file['url'], headers=headers, verify=False)
                        if image_response.status_code == 200:
                            image = Image.open(BytesIO(image_response.content))
                            png_path = local_path.replace('.webp', '.png')
                            image.save(png_path, 'PNG')
                            print(f"Downloaded and converted: {local_path}")
                    elif file['name'].endswith('.mp4'):
                        download_file(file['url'], local_path, headers)
                elif file['type'] == 'FOLDER':
                    new_path_param = urllib.parse.quote(file['path'] + file['name'] + '/')
                    new_url = f"{url.split('?')[0]}?path={new_path_param}"
                    process_directory(new_url, base_output_folder, headers)
            except requests.exceptions.SSLError as e:
                logging.error(f"SSL error for file {local_path}: {e}")
            except Exception as e:
                logging.error(f"Error processing file {local_path}: {e}")

    except requests.exceptions.SSLError as e:
        logging.error(f"SSL error for directory {base_output_folder}: {e}")
    except Exception as e:
        logging.error(f"Error processing directory {url}: {e}")

def main():
    name = '清水由乃'
    photo = ''  # Set to a specific subdirectory name if needed
    base_url = "https://www.cosersets.com/api/list/1"
    output_folder = "/Users/zingliu/Code/coser-download"

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'referer': 'https://www.cosersets.com/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    if photo:
        path_param = f"/{name}/{photo}"
        query_params = {
            'path': path_param,
            'password': '',
            'orderBy': '',
            'orderDirection': ''
        }
        encoded_query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
        url = f"{base_url}?{encoded_query}"
        process_directory(url, output_folder, headers)
    else:
        subdirectories = get_subdirectories(base_url, name)
        for photo in subdirectories:
            print(photo)
            path_param = f"/{name}/{photo}"
            query_params = {
                'path': path_param,
                'password': '',
                'orderBy': '',
                'orderDirection': ''
            }
            encoded_query = urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote)
            url = f"{base_url}?{encoded_query}"
            process_directory(url, output_folder, headers)

if __name__ == "__main__":
    main()