"""
@Author: lin chen
@File: main.py
"""
import json
import sys
import ctypes
import threading

import requests
import subprocess
import re
import os
import time

from mitmproxy import http


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def kill_process():
    try:
        subprocess.run(['taskkill', '/F', '/IM', "直播伴侣.exe"], check=True)
        print(f'已强制结束直播伴侣.exe进程')
    except subprocess.CalledProcessError as e:
        print(f'Error: {e.output}')


def math_push_url_code(url):
    pattern = r'(rtmp://[^/]+/third/)(.+)'
    match = re.search(pattern, url)
    if match:
        rtmp_url = match.group(1)[:-1]  # remove the trailing '?'
        params = match.group(2)
        return rtmp_url, params


lock = threading.Lock()


class Proxy:
    def __init__(self):
        if not is_admin():
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        current_path = os.path.dirname(os.path.abspath('main.py'))
        print(f'文件运行目录:{current_path}')
        print(f'文件所在目录:{sys.path[0]}')
        print('已开始捕获推流，代理端口为：8080')

    log_hosts = ["log-snssdk.zijieapi.com"]
    catch = True

    push_control_data = json.dumps({})
    header = None
    cookies = None
    push_url = None
    time_start = None

    def request(self, flow: http.HTTPFlow):
        if flow.request.pretty_host in self.log_hosts:
            push_data = flow.request.json()
            # 三种状态 1.connect_start 开始连接 2.push_stream 正在推流 3.connect_end 结束连接
            event_key = push_data['data'][0]['event_key']
            if "connect_start" in event_key:
                with open(f"{sys.path[0]}\\start.json", "a+") as f1:
                    f1.write(json.dumps(push_data, indent=4))
                print("检测到直播已开始，准备拦截")
                self.time_start = time.time()
                self.header = flow.request.headers
                self.push_control_data = push_data
                self.cookies = flow.request.cookies

            if "push_stream" in event_key:
                self.push_url = push_data['data'][0]['push_url']
                rtmp_url, params = math_push_url_code(self.push_url)
                print(f"推流地址:{rtmp_url}\n推流码:{params}")
                kill_process()

            # if 'connect_end' in event_key:
            #     with open(f"{sys.path[0]}\\end.json", "a+") as f1:
            #         f1.write(json.dumps(push_data, indent=4))
            #     flow.kill()
            #     print("已拦截抖音直播结束直播请求")
        # with lock:
        #     with open(f"{sys.path[0]}\\tmp\\{flow.request.pretty_host}.txt", 'a+') as f1:
        #         f1.write(flow.request.text+'\n')

    def response(self, flow: http.HTTPFlow):
        pass

    def done(self):
        try:
            print("将同时中断抖音直播")
            end_control_data = self.process_json(self.push_control_data)
            requests.post(url="https://log-snssdk.zijieapi.com/video/v1/live_log/", json=end_control_data,
                                     headers=self.header, cookies=self.cookies)
            response = requests.post(url="https://log-snssdk.zijieapi.com/video/v1/live_log/", json=end_control_data,
                                     headers=self.header, cookies=self.cookies)
            print(response.json())
        except TypeError:
            pass

    def process_json(self, data):
        del data['data'][0]['connect_elapse']
        del data['data'][0]['connect_status']
        del data['data'][0]['gop']
        del data['data'][0]['max_bitrate']
        del data['data'][0]['min_bitrate']
        del data['data'][0]['sdk_param']
        data['data'][0]['push_duration'] = int((self.time_start-time.time())*1000)
        data['data'][0]['reconnect_count'] = 0
        data['data'][0]['send_package_slow_times'] = 0
        data['data'][0]['state'] = 1
        data['data'][0]['is_third_push'] = 0
        data['data'][0]['timestamp'] = int(time.time() * 1000)
        return data


addons = [
    Proxy()
]
