import os
import re
import traceback
from time import sleep
from urllib.parse import urljoin
from selenium.webdriver import Chrome
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

if not os.path.exists("dataset"):
    os.makedirs("dataset")

options = Options()
options.binary_location = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')

web = Chrome(service=Service(ChromeDriverManager().install()), options=options)
base_url = 'https://www1.szu.edu.cn/board/'

web.get(base_url + 'infolist.asp?')
input("请手动登录，登录完成后，按回车继续...")

obj2 = re.compile(r'<a target="_blank" class="fontcolor3" href="(?P<url>.*?)">', re.S)
departments = ['国际交流与合作部', '教务部', '人力资源部', '图书馆', '校医院']

wait = WebDriverWait(web, 15)

for departmentName in departments:
    print(f"开始抓取部门：{departmentName}")
    try:
        web.get(base_url + 'infolist.asp?')
        print(f"页面打开成功: {web.current_url}")
        sleep(2)

        try:
            year_sel_elem = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[1]/td/table/tbody/tr/td[2]/select[1]')))
            print("年份下拉框定位成功")
            year_sel = Select(year_sel_elem)
        except Exception as e:
            print("年份下拉框定位失败")
            raise e

        try:
            dep_sel_elem = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[1]/td/table/tbody/tr/td[2]/select[2]')))
            print("部门下拉框定位成功")
            dep_sel = Select(dep_sel_elem)
        except Exception as e:
            print("部门下拉框定位失败")
            raise e

        print(f"部门选项 for {departmentName}:")
        for option in dep_sel.options:
            print(f"  value={option.get_attribute('value')}, text={option.text.strip()}")

        value_to_select = None
        departmentName_strip = departmentName.strip()

        for option in dep_sel.options:
            option_text = option.text.strip()
    # 改为包含匹配，更灵活一些
            if departmentName_strip in option_text:
                value_to_select = option.get_attribute('value')
                print(f"匹配部门成功: 期望='{departmentName_strip}'，实际='{option_text}'，value={value_to_select}")
                break

        if not value_to_select:
            print(f"[{departmentName}] 未找到对应的部门value，所有部门选项如下：")
            for option in dep_sel.options:
                print(f"  value={option.get_attribute('value')}, text='{option.text.strip()}'")
            continue


        year_sel.select_by_visible_text('2023年')
        dep_sel.select_by_value(value_to_select)
        print(f"选中年份 2023 和部门 {departmentName}（value={value_to_select}）")

        try:
            search_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[1]/td/table/tbody/tr/td[2]/input[3]')
            ))
            print("查询按钮定位成功，点击查询")
            search_btn.click()
        except Exception as e:
            print("查询按钮定位或点击失败")
            raise e

        sleep(2)

        try:
            table = wait.until(EC.presence_of_element_located((By.XPATH, '/html/body/table/tbody/tr[2]/td/table/tbody/tr[3]/td/table/tbody/tr[3]/td')))
            print("公告列表表格定位成功")
        except Exception as e:
            print("公告列表表格定位失败")
            raise e

        table_html = table.get_attribute('innerHTML')
        result = obj2.finditer(table_html)

        os.makedirs(os.path.join("data", departmentName), exist_ok=True)

        for index, item in enumerate(result):
            if index >= 100:
                break

            new_url = urljoin(base_url, item.group('url'))
            print(f"[{departmentName}] 正在抓取第 {index+1} 条公告，链接: {new_url}")
            web.get(new_url)
            sleep(2)

            try:
                content = wait.until(EC.presence_of_element_located(
                    (By.XPATH, '/html/body/table/tbody/tr[1]/td/table/tbody/tr[4]')
                ))
                content_text = content.text.strip()
                print(f"[{departmentName}] 第 {index+1} 条内容获取成功")
            except Exception as e:
                print(f"[{departmentName}] 第 {index+1} 条内容获取失败")
                content_text = "[内容获取失败]"

            file_path = os.path.join("data", departmentName, f"{index+1:03d}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content_text)

            print(f"[{departmentName}] 已保存文件: {file_path}")

        print(f"{departmentName} 抓取完成，共获取 {index+1} 条。")
        print('--------------------------------------------')

    except Exception as e:
        print(f"[{departmentName}] 抓取失败：{e}")
        traceback.print_exc()

web.quit()
