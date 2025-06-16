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

def sanitize_filename(filename):
    return re.sub(r'[\\/:*?"<>|]', '_', filename)

def scrape_announcements():
    options = Options()
    options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')

    web = webdriver.Chrome(service=Service("D:\Webdownload\chromedriver-win64\chromedriver-win64\chromedriver.exe"), options=options)
    wait = WebDriverWait(web, 30)

    base_url = 'https://www1.szu.edu.cn/board/'
    web.get(base_url + 'infolist.asp?')
    input("请手动登录，登录完成后按回车继续...")

    try:
        year_sel_elem = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/select[1]')))
        year_sel = Select(year_sel_elem)
        year_sel.select_by_visible_text('2025年')

        dep_sel_elem = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/select[2]')))
        dep_sel = Select(dep_sel_elem)
        dep_sel.select_by_visible_text('全部发文单位')

        keyword_input = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[2]/td/table/tbody/tr/td[12]/input[1]')))
        keyword_input.clear()
        keyword_input.send_keys('学术讲座')

        search_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[1]/td/table/tbody/tr/td[3]/input[3]')))
        search_btn.click()
        sleep(2)

        table = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[3]/td')))
        obj2 = re.compile(r'<a target="_blank" class="fontcolor3" href="(?P<url>.*?)">', re.S)
        result = obj2.finditer(table.get_attribute('innerHTML'))

        save_dir = os.path.join("dataset", "全部发文单位")
        os.makedirs(save_dir, exist_ok=True)

        for index, item in enumerate(result):
            if index >= 1000:
                break

            news_url = urljoin(base_url, item.group('url'))
            web.get(news_url)
            sleep(2)

            try:
                content_elem = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '/html/body/table/tbody/tr[1]/td/table/tbody/tr[4]')
                ))
                inner_html = content_elem.get_attribute('innerHTML')
                soup = BeautifulSoup(inner_html, 'html.parser')

                # 清理并保留原始换行格式的文本
                raw_text = soup.get_text(separator='\n')
                lines = [line.rstrip() for line in raw_text.split('\n')]
                clean_lines = []
                for line in lines:
                    if line.strip():
                        clean_lines.append(line)
                text_content = '\n'.join(clean_lines).strip()

                # 提取超链接
                links = []
                for a_tag in soup.find_all('a', href=True):
                    full_link = urljoin(news_url, a_tag['href'])
                    links.append(full_link)

                # 保存文件
                save_path = os.path.join(save_dir, f"{index+1:03d}.txt")
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(f"标题：第{index+1}条公告\n\n")
                    f.write("正文：\n")
                    f.write(text_content + "\n\n")
                    if links:
                        f.write("超链接：\n")
                        for link in links:
                            f.write(f"- {link}\n")

                print(f"[已保存] {save_path}")

            except Exception as e:
                print(f"第{index+539}条获取失败：{e}")
                traceback.print_exc()

    except Exception as e:
        print("初始化选择或搜索过程出错")
        traceback.print_exc()

    web.quit()

if __name__ == '__main__':
    scrape_announcements()
