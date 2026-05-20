import os
import random
import sys
from selenium.webdriver.support import expected_conditions as EC, wait
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from base.log_util import global_logger


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
    driver.get("http://192.168.100.110/#/login")
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
        file_path = r"C:\Users\EDY\Desktop\picture\4225db0bfccb456ca90d7a93c937931a.jpeg"
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
    id_front = r"C:\Users\EDY\Desktop\picture\ScreenShot_2026-04-01_091116_358.png"
    # 身份证反面地址
    id_back = r"C:\Users\EDY\Desktop\picture\ScreenShot_2026-04-01_091147_046.png"

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

    # driver.execute_script(f"""
    #     const input = document.querySelector('input[placeholder="请输入法人手机号"]');
    #     input.value = {phone};
    #     input.dispatchEvent(new Event('input'));
    # """)

    # time.sleep(1)

    # 联系人信息
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    driver.execute_script('''
           // 联系人姓名
           const nameInput = document.querySelector('input[placeholder="请输入日常对接人姓名"]');
           nameInput.value = "测试"; 
           nameInput.dispatchEvent(new Event('input'));

           // 联系人手机号
           const phoneInput = document.querySelector('input[placeholder="请输入联系人手机号"]');
           phoneInput.value = "18901454978"; 
           phoneInput.dispatchEvent(new Event('input'));

           // 联系人邮箱（可选）
           const emailInput = document.querySelector('input[placeholder="请输入联系人电子邮箱"]');
           emailInput.value = "235523@qq.com";
           emailInput.dispatchEvent(new Event('input'));
       ''')
    global_logger.info("✅ 联系人信息填写完成")


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
    # 3. 强制解禁（你点不动就是因为这个！）
    driver.execute_script("arguments[0].disabled = false", next_btn)
    # 4. 点击
    next_btn.click()
    global_logger.info("\033[91m-------第一步信息已全部填写完成------\033[0m")



    global_logger.info("\033[91m-------开始第二步输入------\033[0m")
    # 第1个输入框（平台网址）
    inputs = driver.find_elements(By.XPATH, '//input[@placeholder="请输入内容"]')
    inputs[0].send_keys("https://www.baidu.com")

    # 第2个输入框（ICP备案号）
    inputs[1].send_keys("京ICP证123456号")
    global_logger.info("✅ 平台网址和ICP备案号填写完成")
    # time.sleep(1)

    # ====================== 1. 输入【负责人微信】（普通输入框） ======================

    # 第2个输入框（微信号）
    inputs[2].send_keys("safsafasf")
    global_logger.info("✅ 微信填写完成")
    time.sleep(1)


    # ====================== 2. 选择【机构类型】（下拉框） ======================
    driver.execute_script("""
        // 找到机构类型的label
        const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('机构类型'));
        // 找到label后面的input
        const input = label.nextElementSibling.querySelector('input');
        // 点击展开下拉框
        input.click();
    """)
    # 选择民办学校
    driver.execute_script("""
        setTimeout(() => {
            const options = document.querySelectorAll('.el-select-dropdown li');
            const targetLi = Array.from(options).find(li => li.textContent.trim() === '学科类培训机构');
            if (targetLi) targetLi.click();
        }, 500);
    """)

    driver.execute_script("""
            // 课程类型的label
            const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('课程类型'));
            // 找到label后面的input
            const input = label.nextElementSibling.querySelector('input');
            // 点击展开下拉框
            input.click();
        """)
    # 选择是的发生的
    driver.execute_script("""
            setTimeout(() => {
                const options = document.querySelectorAll('.el-select-dropdown li');
                const targetLi = Array.from(options).find(li => li.textContent.trim() === '是的发生的');
                if (targetLi) targetLi.click();
            }, 500);
        """)

    driver.execute_script("""
                // 找到机构类型的label
                const label = Array.from(document.querySelectorAll('label')).find(el => el.textContent.includes('适配用户'));
                // 找到label后面的input
                const input = label.nextElementSibling.querySelector('input');
                // 点击展开下拉框
                input.click();
            """)
    # 选择是的发生的
    driver.execute_script("""
                setTimeout(() => {
                    const options = document.querySelectorAll('.el-select-dropdown li');
                    const targetLi = Array.from(options).find(li => li.textContent.trim() === '考证考公');
                    if (targetLi) targetLi.click();
                }, 500);
            """)

    global_logger.info("课程信息填写完成")


    # --------------------------------------
    driver.execute_script("""
        // 按页面顺序定位：第1个=技术支持，第2个=教研团队介绍
        const textareas = document.querySelectorAll('.el-textarea__inner');
        if (textareas.length >= 2) {
            // 技术支持文本域
            textareas[0].value = "这里填写你的技术支持内容";
            textareas[0].dispatchEvent(new Event('input', { bubbles: true }));

            // 教研团队介绍文本域
            textareas[1].value = "这里填写你的教研团队介绍内容";
            textareas[1].dispatchEvent(new Event('input', { bubbles: true }));

            console.log("✅ 按顺序赋值成功");
        }
    """)
    global_logger.info("技术和校验内容输入结束")


    #  # --- 版权证明---
    classroom_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[text()='版权证明']/following-sibling::div//input[@type='file']"))
    )
    classroom_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))
    time.sleep(2)

    global_logger.info("===========版权证明结束,进入到最后一步提交=========")


    # # -----------------最后一步提交按钮------------------------------

    driver.execute_script("""
          // 找到页面所有按钮
          let buttons = document.querySelectorAll('button');

          // 遍历，只点【文字 = 提交】的按钮
          for(let b of buttons) {
            if (b.innerText.trim() === '提交') {
              b.click();
              console.log('✅ 已点击提交按钮');
            }
          }
        """)

    global_logger.info("===========提交成功,进程已结束=========")
















