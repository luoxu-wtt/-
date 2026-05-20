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

def init_driver():
    """初始化浏览器驱动"""
    options = Options()
    # 绕过自动化检测提示
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(options=options)
    return driver

def test_login(driver):
    driver.get("http://192.168.100.110/#/login")
    time.sleep(1)
    #  # 输入账号
    #  # driver.execute_script('''
    #      document.querySelector('input[placeholder="请输入账号"]').value = "18888888888";
    #      document.querySelector('input[placeholder="请输入账号"]').dispatchEvent(new Event('input'));
    #  ''')
    # #
    #  # 输入密码
    #  driver.execute_script('''
    #      document.querySelector('input[placeholder="请输入密码"]').value = "123456";
    #      document.querySelector('input[placeholder="请输入密码"]').dispatchEvent(new Event('input'));
    #  ''')

    # # ========== XPath 点击登录按钮 ==========
login_btn = driver.find_element("xpath", '//*[@id="app"]/div/div[2]/div/form/div[3]/div/button/span')
login_btn.click()
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


    # 线下机构
driver.execute_script('''
           // 1. 勾选协议
           const checkbox = document.querySelector('input[type="checkbox"]');
           checkbox.checked = true;
           checkbox.dispatchEvent(new Event('change'));

           const btns = document.querySelectorAll('button');
           btns[0].click();
           btns[0].dispatchEvent(new Event('click'));
       ''')
global_logger.info("协议已勾选")

global_logger.info("==================线上商家入驻开始===================")

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
except  Exception  as  e:
        global_logger.error(f"上传营业执照出错：{e}")
        sys.exit("营业执照有问题,进程结束")


    # 身份证正面
id_front = r"C:\Users\EDY\Desktop\picture\ScreenShot_2026-04-01_091116_358.png"
    # 身份证反面（替换成你的路径）
id_back = r"C:\Users\EDY\Desktop\picture\ScreenShot_2026-04-01_091147_046.png"

    # 获取所有上传框
uploads = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, '//input[@type="file"]'))
    )
    # 上传正面（索引1）
uploads[1].send_keys(id_front)
    # time.sleep(2)

    # 上传反面（索引2）
uploads[2].send_keys(id_back)
global_logger.info("✅ 身份证正反面上传成功")
    # time.sleep(2)
list=['138','182','187']
    a=random.choice(list)
    b="000000"
    c=random.randint(10,99)
    try:
        phone = f"{a}{b}{c}"
    except  Exception  as   e:
        sys.exit("手机号模块有问题,进程已结束")

    global_logger.info(f"✅ 联系方式：{phone}")

    # 法人联系方式
    driver.execute_script('''
        document.querySelector('input[placeholder="请输入法人手机号"]').value =18200000002;
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
    # time.sleep(1)
    driver.execute_script('''
           // 联系人姓名
           const nameInput = document.querySelector('input[placeholder="请输入日常对接人姓名"]');
           nameInput.value = "测试"; 
           nameInput.dispatchEvent(new Event('input'));

           // 联系人手机号
           const phoneInput = document.querySelector('input[placeholder="请输入联系人手机号"]');
           phoneInput.value = "15959549878"; 
           phoneInput.dispatchEvent(new Event('input'));
           
           // 联系人邮箱（可选）
           const emailInput = document.querySelector('input[placeholder="请输入联系人电子邮箱"]');
           emailInput.value = "235523@qq.com";
           emailInput.dispatchEvent(new Event('input'));
       ''')
    global_logger.info("✅ 联系人信息填写完成")
    time.sleep(1)

# 结算信息
    # 对公账户卡号
    driver.execute_script('''
                        document.querySelector('input[placeholder="请输入银行账号"]').value =2353534543534545;
                        document.querySelector('input[placeholder="请输入银行账号"]').dispatchEvent(new Event('input'));
                    ''')
    # time.sleep(1)

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

    # 点击下一步按钮
    next_btn = driver.find_element(By.XPATH, '//button[normalize-space()="下一步"]')
    driver.execute_script("arguments[0].disabled = false", next_btn)
    next_btn.click()

    global_logger.info("\033[91m-------第一步信息已全部填写完成------\033[0m")
    time.sleep(1)

    global_logger.info("\033[91m-------开始第二步输入------\033[0m")

    driver.execute_script('''
        const nameInput = document.querySelector('input[placeholder="请输入校区名称"]');
        nameInput.value = "上海市浦东新区信息技术公司";
        nameInput.dispatchEvent(new Event('input'));
        // 地址
        const addrInput = document.querySelector('input[placeholder="请输入校区详细地址"]');
        addrInput.value = "上海市闵行区1739弄70号";
        addrInput.dispatchEvent(new Event('input'));
        //  校区面积
        const areaInput = document.querySelector('input[placeholder="请输入校区面积（单位：平方米）"]');
        areaInput.value = "108";
        areaInput.dispatchEvent(new Event('input'));
        //  教室数量
        const classInput = document.querySelector('input[placeholder*="教室数量"]') || document.querySelector('//label[text()="* 教室数量"]/following-sibling::div//input');
        classInput.value = "189";
        classInput.dispatchEvent(new Event('input'));
    ''')

    all_inputs = WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, '//input[@type="number"]'))
    )
    print(f"✅ 找到 {len(all_inputs)} 个数字输入框")
    for i, inp in enumerate(all_inputs):
        print(f"索引 {i}：{inp.get_attribute('value')}")

    # ===================== 2. 按真实索引赋值（100%精准） =====================
    # 按页面顺序：教室数量[0] → 在读学生数[1] → 教师人数[2]
    # 先清空默认值0，再输入
    all_inputs[1].clear()
    all_inputs[1].send_keys("500")
    driver.execute_script('arguments[0].dispatchEvent(new Event("input"));', all_inputs[1])
    # time.sleep(1)

    all_inputs[2].clear()
    all_inputs[2].send_keys("20")
    driver.execute_script('arguments[0].dispatchEvent(new Event("input"));', all_inputs[2])
    time.sleep(1)
    global_logger.info("\033[91m-------校区信息填写完成------\033[0m")


    driver.execute_script('''
        // 获取所有复选框的标签（按页面顺序：幼儿教育[0] -> 家庭教育[1]...）
        const labels = document.querySelectorAll('.el-checkbox__label');
        const checkbox = labels[0].previousElementSibling; // 找到第一个复选框

        // 强制勾选
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        labels[0].click(); // 点击标签
    ''')
    # time.sleep(1)
    global_logger.info("\033[91m-------办学范围填写完成------\033[0m")

    course_intro = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//textarea[@placeholder="请输入内容"]'))
    )
    course_intro.send_keys("本机构专注于K12学科教育、幼儿启蒙教育，提供专业的师资团队与舒适的学习环境，助力学生全面发展。")
    global_logger.info("课程介绍输入完毕")
    time.sleep(1)


    # 营业时间输入
    wait = WebDriverWait(driver, 15)
    # 勾选周一
    monday = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[text()='周一']/preceding-sibling::span"))
    )
    if not monday.is_selected():
        monday.click()

    # 1. 正确定位时间输入框
    # ==============================================
    time_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[text()='工作日时间']/following-sibling::div//input"))
    )

    # 2. 修复JS赋值 + 触发事件（核心修复）
    # ==============================================
    target_time = "07:37 至 18:37"
    # 1. 赋值
    driver.execute_script("arguments[0].value = arguments[1]", time_input, target_time)
    # 2. 触发input事件
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'))", time_input)
    # 3. 触发change事件
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", time_input)

    #  -------周末时间----------
    monday = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[text()='周日']/preceding-sibling::span"))
    )
    if not monday.is_selected():
        monday.click()

    # 1. 正确定位时间输入框
    time_input = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[text()='周末时间']/following-sibling::div//input"))
    )

    # 2. 修复JS赋值 + 触发事件（核心修复）
    target_time = "07:37 至 18:37"
    # 1. 赋值
    driver.execute_script("arguments[0].value = arguments[1]", time_input, target_time)
    # 2. 触发input事件
    driver.execute_script("arguments[0].dispatchEvent(new Event('input'))", time_input)
    # 3. 触发change事件
    driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", time_input)
    global_logger.info("===========营业时间已经选择完毕=========")


    #  上传校区租赁
    file_list = [
        r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png",
        r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091116_358.png"
    ]

    for file in file_list:
        upload_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'upload')]//input[@type='file']"))
        )
        upload_input.send_keys(os.path.abspath(file))

    global_logger.info("===========校区图片上传完毕=========")


    # --------------------------------------
    door_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//*[text()='门头照片']/following-sibling::div//input[@type='file']"))
    )
    door_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))


    # --- 3. 前台照片 ---
    front_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//*[text()='前台照片']/following-sibling::div//input[@type='file']"))
    )
    front_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))


    # --- 4. 教室照片 ---
    classroom_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//*[text()='教室照片']/following-sibling::div//input[@type='file']"))
    )
    classroom_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))
    time.sleep(1)



    global_logger.info("===========校区图实景照片成功上传=========")
     # --- 消防验收合格证明 ---
    classroom_input = wait.until(
        EC.presence_of_element_located((By.XPATH, "//*[text()='消防验收合格证明']/following-sibling::div//input[@type='file']"))
    )
    classroom_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))



    global_logger.info("===========消防验收成功上传=========")
    # --- 办学许可证 ---
    classroom_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[text()='办学许可证']/following-sibling::div//input[@type='file']"))
    )
    classroom_input.send_keys(os.path.abspath(r"C:/Users/EDY/Desktop/picture/ScreenShot_2026-04-01_091147_046.png"))
    global_logger.info("===========消办学许可证成功上传,到最后一步提交=========")




    global_logger.info("===========进入到最后一步提交=========")
# -----------------最后一步提交按钮------------------------------

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

if __name__ == "__main__":
    driver = init_driver()
    try:
        test_login(driver)
    finally:
        # 测试结束后关闭浏览器，调试时可注释掉
        driver.quit()






















