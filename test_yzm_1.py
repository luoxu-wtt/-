import random
import time
import ddddocr
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ====================== 启动浏览器（直接运行） ======================
def init_driver():
    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--start-maximized")
    # 保持浏览器不关闭
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    return driver


# ====================== 登录 + 滑块验证 ======================
def run_login():
    driver = init_driver()

    try:
        # 打开登录页
        #driver.get("http://192.168.100.110/#/login")
        driver.get("http://192.168.100.110/merchant/#/login?redirect=/home/home-child")
        time.sleep(1)

        # 输入账号
        driver.execute_script('''
            document.querySelector('input[placeholder="请输入账号"]').value = "18888888888";
            document.querySelector('input[placeholder="请输入账号"]').dispatchEvent(new Event('input'));
        ''')
        time.sleep(0.5)

        # 输入密码
        driver.execute_script('''
            document.querySelector('input[placeholder="请输入密码"]').value = "123456";
            document.querySelector('input[placeholder="请输入密码"]').dispatchEvent(new Event('input'));
        ''')
        time.sleep(0.5)

        # 点击登录
        login_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//*[contains(@class,"btn") and contains(string(),"登录")]')
            )
        )
        driver.execute_script("arguments[0].click();", login_btn)
        time.sleep(1)

        # ======================= 滑块验证 =======================
        ocr = ddddocr.DdddOcr(det=False, ocr=False, show_ad=False)

        def get_gap_distance():
            captcha = driver.find_element(By.ID, "slideVerify")
            captcha.screenshot("captcha.png")
            with open("captcha.png", "rb") as f:
                img_bytes = f.read()
            res = ocr.slide_match(img_bytes, img_bytes, simple_target=True)

            if isinstance(res, dict):
                gap_x = res.get("target", [0])[0]
            else:
                gap_x = res[0]

            return gap_x + 15

        def human_slide(distance):
            slider = driver.find_element(By.CLASS_NAME, "slide-verify-slider-mask-item")
            action = ActionChains(driver)
            action.click_and_hold(slider).perform()
            time.sleep(random.uniform(0.2, 0.4))

            moved = 0
            while moved < distance:
                if moved < distance * 0.6:
                    step = random.randint(6, 10)
                    t = random.uniform(0.09, 0.14)
                elif moved < distance * 0.9:
                    step = random.randint(10, 16)
                    t = random.uniform(0.06, 0.1)
                else:
                    step = random.randint(3, 6)
                    t = random.uniform(0.12, 0.2)

                step = min(step, distance - moved)
                action.move_by_offset(step, random.randint(-1, 1)).perform()
                time.sleep(t)
                moved += step

                if moved < distance and random.random() < 0.25:
                    back = random.randint(1, 3)
                    action.move_by_offset(-back, 0).perform()
                    time.sleep(random.uniform(0.03, 0.06))
                    action.move_by_offset(back, 0).perform()
                    time.sleep(random.uniform(0.03, 0.06))

            time.sleep(random.uniform(0.2, 0.4))
            action.release().perform()
            time.sleep(1)

        print("正在识别缺口...")
        distance = get_gap_distance()
        print(f"缺口距离：{distance}")
        human_slide(distance)
        print("✅ 登录 + 滑块验证完成！")

    except Exception as e:
        print(f"执行异常：{e}")


# ====================== 直接启动 ======================
if __name__ == "__main__":
    print("正在启动自动化脚本...")
    run_login()