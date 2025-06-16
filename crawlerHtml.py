import os
import re
import traceback
from time import sleep
from urllib.parse import urljoin, urlparse
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from bs4 import BeautifulSoup
import requests

def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def get_cookies_dict(driver):
    # 从 Selenium 浏览器获取 cookie 转成 requests 可用格式
    return {cookie['name']: cookie['value'] for cookie in driver.get_cookies()}

def download_and_replace_images(soup, base_url, img_dir, cookies=None):
    os.makedirs(img_dir, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Referer": base_url
    }
    for i, img in enumerate(soup.find_all('img')):
        src = img.get('src')
        # 检查懒加载属性
        if not src:
            src = img.get('data-src') or img.get('data-original')
        if not src:
            continue

        img_url = urljoin(base_url, src)
        img_name = f"img{i+1}_{sanitize_filename(os.path.basename(urlparse(img_url).path))}"
        img_path = os.path.join(img_dir, img_name)
        try:
            print(f"下载图片: {img_url}")
            resp = requests.get(img_url, headers=headers, cookies=cookies, timeout=10)
            resp.raise_for_status()
            with open(img_path, 'wb') as f:
                f.write(resp.content)
            img['src'] = os.path.join('images', img_name).replace('\\', '/')
        except Exception as e:
            print(f"[图片下载失败]")

def scrape_announcements():
    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')

    web = webdriver.Chrome(service=Service("D:\\Webdownload\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"), options=options)
    wait = WebDriverWait(web, 30)

    base_url = 'https://www1.szu.edu.cn/board/'
    web.get(base_url + 'infolist.asp?')
    input("请手动登录，登录完成后按回车继续...")

    try:
        year_sel_elem = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/select[1]')))
        year_sel = Select(year_sel_elem)
        year_sel.select_by_visible_text('2021年')

        dep_sel_elem = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/select[2]')))
        dep_sel = Select(dep_sel_elem)
        dep_sel.select_by_visible_text('全部发文单位')

        keyword_input = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/input[1]')))
        keyword_input.clear()
        keyword_input.send_keys('学术讲座')

        search_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[1]/td/table/tbody/tr/td[3]/input[3]')))
        search_btn.click()
        sleep(2)

        table = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[3]/td')))
        obj2 = re.compile(r'<a target="_blank" class="fontcolor3" href="(?P<url>.*?)">', re.S)
        result = obj2.finditer(table.get_attribute('innerHTML'))

        save_dir = os.path.join("dataset_html", "全部发文单位")
        os.makedirs(save_dir, exist_ok=True)

        # 获取当前浏览器登录态的cookie，用于requests请求带上
        cookies = get_cookies_dict(web)

        for index, item in enumerate(result):
            if index >= 1000:
                break

            news_url = urljoin(base_url, item.group('url'))
            web.get(news_url)
            sleep(2)

            try:
                content_elem = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '/html/body/table/tbody/tr[1]/td/table/tbody/tr[4]')))
                inner_html = content_elem.get_attribute('innerHTML')
                soup = BeautifulSoup(inner_html, 'html.parser')

                news_folder = os.path.join(save_dir, f"{index+1:03d}")
                img_dir = os.path.join(news_folder, "images")
                os.makedirs(news_folder, exist_ok=True)

                # 传入cookies参数进行图片下载
                download_and_replace_images(soup, news_url, img_dir, cookies=cookies)

                html_path = os.path.join(news_folder, "index.html")
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(str(soup))

                print(f"[已保存] 第{index+1}条公告 HTML：{html_path}")

            except Exception as e:
                print(f"第{index+1}条获取失败：{e}")
                traceback.print_exc()

    except Exception as e:
        print("初始化选择或搜索过程出错")
        traceback.print_exc()

    web.quit()

if __name__ == '__main__':
    scrape_announcements()
