import os
import random
import sys
from selenium.webdriver.support import expected_conditions as EC
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from base.log_util import global_logger

# ================== 随机手机号函数（已补上） ==================
def generate_phone():
    prefix = random.choice([
        '130', '131', '132', '135', '136', '137', '138', '139',
        '150', '151', '152', '155', '156', '158', '159',
        '176', '177', '181', '182', '183', '185', '186', '187', '188', '189'
    ])
    suffix = ''.join(random.choices('0123456789', k=8))
    return prefix + suffix

def init_driver():
    """初始化浏览器驱动（正式运行用）"""
    options = Options()
    # 绕过自动化检测提示
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")  # 窗口最大化

    # 核心：让浏览器执行完不关闭
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=options)
    return driver

@pytest.fixture
def driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    pass

def test_login(driver):

    wait = WebDriverWait(driver, 15)
    driver.get("http://192.168.100.110/merchant/#/login?redirect=/home/home-child")
    #driver.get("http://192.168.100.110/#/login")
    time.sleep(1)

    global_logger.info("==================线下商家入驻开始===================")
    driver.execute_script('''
            // 点击商家入驻
            document.querySelectorAll('*').forEach(el => {
                if(el.textContent.includes("商家入驻")) {
                    el.click();
                    console.log("已点击商家入驻");
                }
            });
        ''')


    time.sleep(1)
    # 勾选协议 + 点确定入驻
    driver.execute_script('''
            // 勾选协议
            document.querySelector('input[type="checkbox"]').checked = true;
            document.querySelector('input[type="checkbox"]').dispatchEvent(new Event('change'));

            // 点所有确定入驻按钮
            document.querySelectorAll('button').forEach(btn => {
                if(btn.textContent === "确定入驻") btn.click();
            });
        ''')


    global_logger.info("==================线上商家入驻开始===================")
     # 线上机构流程
    driver.execute_script('''
                   // 1. 勾选协议
                   const checkbox = document.querySelector('input[type="checkbox"]');
                   checkbox.checked = true;
                   checkbox.dispatchEvent(new Event('change'));

                   const btns = document.querySelectorAll('button');
                   btns[1].click();
                   btns[1].dispatchEvent(new Event('click'));
               ''')


    #  上传营业执照
    try:
        file_path = r"D:\rz\4225db0bfccb456ca90d7a93c937931a.jpeg"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在：{file_path}")

        upload_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="file"]'))
        )
        upload_input.send_keys(file_path)
        time.sleep(1)
    except  Exception as e:
        global_logger.error(f"上传营业执照出错：{e}")
        sys.exit("营业执照有问题,进程结束")

    # 身份证正面地址
    driver.execute_script("""
                        setTimeout(() => {
                            const options = document.querySelectorAll('.el-select-dropdown li');
                            const targetLi = Array.from(options).find(li => li.textContent.trim() === '大陆身份证');
                            if (targetLi) targetLi.click();
                        }, 500);
                    """)
    time.sleep(1)
    id_front = r"D:\rz\1.jpg"
    # 身份证反面地址
    id_back = r"D:\rz\2.jpg"

    # 获取所有上传框
    uploads = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, '//input[@type="file"]'))
    )
    # 上传正面（索引1）
    uploads[1].send_keys(id_front)
    time.sleep(1)

    # 上传反面（）
    uploads[2].send_keys(id_back)
    global_logger.info("✅ 身份证正反面上传成功")
    time.sleep(1)
    list = ['138', '182', '187']
    a = random.choice(list)
    b = "000000"
    c = random.randint(10, 99)
    try:
        phone = f"{a}{b}{c}"
    except  Exception as e:
        sys.exit("手机号模块有问题,进程已结束")

    global_logger.info(f"✅ 联系方式：{phone}")

    # 法人联系方式
    driver.execute_script('''
        document.querySelector('input[placeholder="请输入法人手机号"]').value =18700000001;
        document.querySelector('input[placeholder="请输入法人手机号"]').dispatchEvent(new Event('input'));
    ''')

    # ================== 随机联系人手机号（已修复） ==================
    contact_phone = generate_phone()
    global_logger.info(f"✅ 随机生成联系人手机号：{contact_phone}")

    # 联系人信息
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script('''
           // 联系人姓名
           const nameInput = document.querySelector('input[placeholder="请输入日常对接人姓名"]');
           nameInput.value = "测试"; 
           nameInput.dispatchEvent(new Event('input'));

           // 联系人手机号
           const phoneInput = document.querySelector('input[placeholder="请输入联系人手机号"]');
           phoneInput.value = arguments[0]; 
           phoneInput.dispatchEvent(new Event('input'));

           // 联系人邮箱（可选）
           const emailInput = document.querySelector('input[placeholder="请输入联系人电子邮箱"]');
           emailInput.value = "235523@qq.com";
           emailInput.dispatchEvent(new Event('input'));
       ''', contact_phone)
    global_logger.info("✅ 联系人信息填写完成（手机号随机）")
    time.sleep(1)

    # 结算信息模块
    # 对公账户卡号
    driver.execute_script('''
                        document.querySelector('input[placeholder="请输入银行账号"]').value =2353534543534545;
                        document.querySelector('input[placeholder="请输入银行账号"]').dispatchEvent(new Event('input'));
                    ''')

    # 承诺书
    driver.execute_script('''
            // 1. 填充开户银行
            const bankInput = document.querySelector('input[placeholder*="需精确到支行"]');
            bankInput.value = "中国工商银行北京市朝阳支行";
            bankInput.dispatchEvent(new Event('input'));

            // 2. 勾选入驻承诺书
            document.querySelector('input[type="checkbox"]').checked = true;
            document.querySelector('input[type="checkbox"]').dispatchEvent(new Event('change'));
        ''')

    global_logger.info("结算信息填写完成,承诺书已勾选")
    time.sleep(1)

    # 点击下一步
    next_btn = driver.find_element(By.XPATH, '//button[normalize-space()="下一步"]')
    driver.execute_script("arguments[0].disabled = false", next_btn)
    next_btn.click()
    global_logger.info("\033[91m-------第一步信息已全部填写完成------\033[0m")

    global_logger.info("\033[91m-------开始第二步输入------\033[0m")
    # 第1个输入框（平台网址）
    inputs = driver.find_elements(By.XPATH, '//input[@placeholder="请输入内容"]')
    inputs[0].send_keys("https://www.baidu.com")

    # 第2个输入框（ICP备案号）
    inputs[1].send_keys("京ICP证123456号")
    global_logger.info("✅ 平台网址和ICP备案号填写完成")

    # 第2个输入框（微信号）
    inputs[2].send_keys("safsafasf")
    global_logger.info("✅ 微信填写完成")
    time.sleep(1)

    # ====================== 选择【机构类型】 ======================
    driver.execute_script("""
        const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('机构类型'));
        const input = label.nextElementSibling.querySelector('input');
        input.click();
    """)
    driver.execute_script("""
        setTimeout(() => {
            const options = document.querySelectorAll('.el-select-dropdown li');
            const targetLi = Array.from(options).find(li => li.textContent.trim() === '学科类培训机构');
            if (targetLi) targetLi.click();
        }, 500);
    """)

    driver.execute_script("""
            const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('课程类型'));
            const input = label.nextElementSibling.querySelector('input');
            input.click();
        """)
    driver.execute_script("""
            setTimeout(() => {
                const options = document.querySelectorAll('.el-select-dropdown li');
                const targetLi = Array.from(options).find(li => li.textContent.trim() === '发多少发多少');
                if (targetLi) targetLi.click();
            }, 500);
        """)

    driver.execute_script("""
                const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('适配用户'));
                const input = label.nextElementSibling.querySelector('input');
                input.click();
            """)
    driver.execute_script("""
                setTimeout(() => {
                    const options = document.querySelectorAll('.el-select-dropdown li');
                    const targetLi = Array.from(options).find(li => li.textContent.trim() === '考证考公');
                    if (targetLi) targetLi.click();
                }, 500);
            """)

    driver.execute_script("""
                    setTimeout(() => {
                        const options = document.querySelectorAll('.el-select-dropdown li');
                        const targetLi = Array.from(options).find(li => li.textContent.trim() === '线上色粉');
                        if (targetLi) targetLi.click();
                    }, 500);
                """)
    # 店铺等级
    # driver.find_element(By.XPATH,'//*[@id="el-id-1294-91"]').click()
    # wait = WebDriverWait(driver, 10)
    # wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="普通店铺"]'))).click()
    # driver.find_element(By.XPATH,
    #                     '//*[@id="app"]/div/div[3]/div/div[1]/form/div[10]/div/div/div/div[1]/div[2]').click()
    # wait = WebDriverWait(driver, 10)
    # wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="普通店铺"]'))).click()

    global_logger.info("课程信息填写完成")

    driver.execute_script("""
        const textareas = document.querySelectorAll('.el-textarea__inner');
        if (textareas.length >= 2) {
            textareas[0].value = "这里填写你的技术支持内容";
            textareas[0].dispatchEvent(new Event('input', { bubbles: true }));
            textareas[1].value = "这里填写你的教研团队介绍内容";
            textareas[1].dispatchEvent(new Event('input', { bubbles: true }));
            console.log("✅ 按顺序赋值成功");
        }
    """)
    global_logger.info("技术和校验内容输入结束")

    # --- 版权证明---
    classroom_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[text()='版权证明']/following-sibling::div//input[@type='file']"))
    )
    classroom_input.send_keys(os.path.abspath(r"D:\rz\znt\ket考冲班_03.jpg"))
    time.sleep(2)

    global_logger.info("===========版权证明结束,进入到最后一步提交=========")

    # 提交
    driver.execute_script("""
          let buttons = document.querySelectorAll('button');
          for(let b of buttons) {
            if (b.innerText.trim() === '提交') {
              b.click();
              console.log('✅ 已点击提交按钮');
            }
          }
        """)

    global_logger.info("===========提交成功,进程已结束=========")


if __name__ == "__main__":
    print("正在启动商家入驻自动化脚本...")
    driver = init_driver()

    try:
        test_login(driver)
    except Exception as e:
        print(f"脚本执行异常：{e}")
        global_logger.error(f"脚本异常终止：{str(e)}")
    finally:
        #已经注释，绝对不关闭浏览器
        #driver.quit()
        print("✅ 脚本执行完成，浏览器保持打开！")