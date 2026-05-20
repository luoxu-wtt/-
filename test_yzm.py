import base64
import math
import os
import random
import sys
import time
from io import BytesIO
from pathlib import Path
from selenium.webdriver.support import expected_conditions as EC
import cv2
import numpy as np
from DrissionPage import ChromiumOptions, ChromiumPage
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support import wait
from base.log_util import global_logger


LOGIN_URL = "http://192.168.100.110/merchant/#/login?redirect=/home/home-child"
ACCOUNT = "18888888888"
PASSWORD = "123456"

SEL_ACCOUNT = "css:.login-form .el-form-item:nth-of-type(1) input.el-input__inner"
SEL_PASSWORD = "css:.login-form .el-form-item:nth-of-type(2) input.el-input__inner"
SEL_LOGIN_BTN = "css:button.login-btn"
SEL_CAPTCHA = "css:#slideVerify"
SEL_SLIDER_BTN = "css:.slide-verify-slider-mask-item"
SEL_REFRESH = "css:.slide-verify-refresh-icon"
MAX_CAPTCHA_RETRY = 6


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

# ---------------启动浏览器--------
def get_page(port: int = 9222) -> ChromiumPage:
    try:
        page = ChromiumPage(addr_or_opts=f"127.0.0.1:{port}")
        global_logger.info(f"已连接到已运行的浏览器 (port={port})")
        return page
    except Exception:
        pass

    user_data_dir = get_app_dir() / "browser_data_dtt"
    user_data_dir.mkdir(exist_ok=True)
    opts = ChromiumOptions()
    opts.set_local_port(port)
    opts.set_user_data_path(str(user_data_dir))
    opts.auto_port(False)
    global_logger.info(f"启动新的浏览器实例 (port={port})")
    return ChromiumPage(addr_or_opts=opts)

def decode_canvas_data_url(data_url: str) -> np.ndarray:
    raw = base64.b64decode(data_url.split(",", 1)[1])
    pil = Image.open(BytesIO(raw)).convert("RGBA")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGBA2BGRA)


global_logger.info("识别缺口开始计算滑动距离")
def find_gap_x(page: ChromiumPage) -> int:
    """Find drag distance in canvas pixels.
    The bg canvas has a bright-white puzzle-shaped highlight marking the gap.
    We threshold for bright pixels and template-match the piece's alpha shape
    against that binary map.
    """

    js = """
    const sv = document.getElementById('slideVerify');
    if (!sv) return null;
    const canvases = sv.querySelectorAll('canvas');
    if (canvases.length < 2) return null;
    return {
      bg: canvases[0].toDataURL('image/png'),
      block: canvases[1].toDataURL('image/png'),
    };
    """
    data = page.run_js(js)
    if not data:
        raise RuntimeError("无法读取 captcha canvas 数据")

    bg = decode_canvas_data_url(data["bg"])
    block = decode_canvas_data_url(data["block"])

    bg_gray = cv2.cvtColor(cv2.cvtColor(bg, cv2.COLOR_BGRA2BGR), cv2.COLOR_BGR2GRAY)
    alpha = block[:, :, 3]

    ys, xs = np.where(alpha > 128)
    if len(xs) == 0:
        raise RuntimeError("puzzle 块 alpha 全透明")
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    piece_mask = (alpha[y0:y1, x0:x1] > 128).astype(np.uint8) * 255

    best_score = -1.0
    best_x = None
    for th in (210, 200, 190, 180):
        bright = (bg_gray > th).astype(np.uint8) * 255
        res = cv2.matchTemplate(bright, piece_mask, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = max_val
            best_x = max_loc[0]

    global_logger.info(
        f"Gap 匹配 score={best_score:.3f}, gap_x={best_x}, "
        f"piece 起点={x0}, bg={bg.shape[1]}x{bg.shape[0]}")

#未找到滑动距离
    if best_x is None:
        raise RuntimeError("未找到 gap")
    block_target_left = best_x - x0
    # vue-monoplasty-slide-verify: blockLeft = (w-60)/(w-40) * mouseDx, w=370
    # so mouseDx = blockLeft / 0.9394 (for w=370)
    mouse_distance = int(round(block_target_left / 0.9394))
    return max(1, mouse_distance)


def generate_tracks(distance: int) -> list[tuple[int, float]]:
    overshoot = max(3, round(distance * 0.08))
    fwd = distance + overshoot
    p1 = max(3, fwd // 5)
    p3 = max(2, fwd // 6)
    p2 = fwd - p1 - p3
    return [
        (p1, 0.15),
        (p2, 0.35),
        (p3, 0.20),
        (-overshoot, 0.20),
    ]


def _cdp_mouse(page: ChromiumPage, event_type: str, x: float, y: float) -> None:
    page.run_cdp(
        "Input.dispatchMouseEvent",
        type=event_type,
        x=float(x),
        y=float(y),
        button="left",
        buttons=1 if event_type != "mouseReleased" else 0,
        clickCount=1,
    )


global_logger.info("根据距离滑动代码")
def drag_slider(page: ChromiumPage, distance: int) -> None:
    rect = None
    for _ in range(20):
        rect = page.run_js(
            "const b=document.querySelector('.slide-verify-slider-mask-item');"
            "if(!b) return null;"
            "const r=b.getBoundingClientRect();"
            "return {x:r.left+r.width/2, y:r.top+r.height/2, w:r.width, h:r.height};"
        )
        if rect and rect.get("w", 0) > 10:
            break
        time.sleep(0.1)
    if not rect or rect.get("w", 0) <= 10:
        raise RuntimeError(f"找不到滑块按钮: rect={rect}")

    start_x, start_y = rect["x"], rect["y"]

    global_logger.info(f"起点=({start_x:.1f},{start_y:.1f}), 拖动距离={distance}px")

    _cdp_mouse(page, "mouseMoved", start_x, start_y)
    time.sleep(random.uniform(0.05, 0.1))
    _cdp_mouse(page, "mousePressed", start_x, start_y)
    time.sleep(random.uniform(0.1, 0.2))

    phases = generate_tracks(distance)
    cur_x, cur_y = start_x, start_y
    for px, dur in phases:
        steps = max(5, abs(px) // 3)
        for i in range(1, steps + 1):
            t = i / steps
            nx = cur_x + px * t
            ny = cur_y + random.uniform(-0.5, 0.5)
            _cdp_mouse(page, "mouseMoved", nx, ny)
            time.sleep(dur / steps)
        cur_x += px
        cur_y = ny

    time.sleep(random.uniform(0.1, 0.2))
    _cdp_mouse(page, "mouseReleased", cur_x, cur_y)




def captcha_solved(page: ChromiumPage) -> bool:
    """Captcha dialog disappears on success."""
    ele = page.ele(SEL_CAPTCHA, timeout=0.5)
    if not ele:
        return True
    try:
        return not ele.states.is_displayed
    except Exception:
        return False


def refresh_captcha(page: ChromiumPage) -> None:
    try:
        page.run_js(
            "const b=document.querySelector('.slide-verify-refresh-icon');"
            "if(b) b.click();"
        )
        time.sleep(0.8)
    except Exception as exc:

        global_logger.info(f"刷新 captcha 异常: {exc}")


def solve_captcha(page: ChromiumPage) -> bool:
    for attempt in range(1, MAX_CAPTCHA_RETRY + 1):
        # wait for canvases to be drawn
        time.sleep(0.8)
        try:
            distance = find_gap_x(page)

            global_logger.info(f"第 {attempt} 次尝试, 拖动距离={distance}px")
            drag_slider(page, distance)

        except Exception as exc:

            global_logger.info(f"captcha 求解异常: {exc}")
            refresh_captcha(page)
            continue

        time.sleep(1.5)
        if captcha_solved(page):

            global_logger.info("滑块验证通过")
            return True



        global_logger.info(f"第 {attempt} 次滑块验证失败, 准备刷新")
        refresh_captcha(page)

    return False



global_logger.info("---代码拖动完毕-----")


def wait_captcha_appear(page: ChromiumPage, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        ele = page.ele(SEL_CAPTCHA, timeout=0.3)
        if ele:
            try:
                if ele.states.is_displayed:
                    return True
            except Exception:
                return True
        time.sleep(0.2)
    return False


def is_logged_in(page: ChromiumPage) -> bool:
    url = page.url or ""
    return "/login" not in url

# --------------------------登录逻辑-----------------------------------
def login(page: ChromiumPage) -> bool:

    global_logger.info(f"打开登录页: {LOGIN_URL}")
    page.get(LOGIN_URL)
    time.sleep(1.0)

    acc = page.ele(SEL_ACCOUNT, timeout=10)
    pwd = page.ele(SEL_PASSWORD, timeout=5)
    if not acc or not pwd:

        global_logger.error("账号/密码输入框未找到")
        return False
    acc.input(ACCOUNT, clear=True)
    pwd.input(PASSWORD, clear=True)

    global_logger.info("已填入账号密码")

    btn = page.ele(SEL_LOGIN_BTN, timeout=5)
    if not btn:

        global_logger.error("登录按钮未找到")
        return False
    btn.click()

    global_logger.info("已点击登录")

    # -----------开始执行滑动----------------------------------------

    if not wait_captcha_appear(page, timeout=8.0):
        time.sleep(2.0)
        if is_logged_in(page):

            global_logger.info("无需验证码, 已登录")
            return True

        global_logger.error("未检测到滑块验证, 也未跳转")
        return False

    if not solve_captcha(page):

        global_logger.error("滑块验证多次失败")
        return False


    deadline = time.time() + 10
    while time.time() < deadline:
        if is_logged_in(page):

            global_logger.info(f"登录成功, 当前 URL: {page.url}")

            return True
        time.sleep(0.3)


    global_logger.info(f"滑块已过但未跳转, 当前 URL: {page.url}")
    return False

#
# global_logger.info("---325行-----")
# def  reg(page: ChromiumPage):
#     global_logger.info("进入用户管理327行")
#     perm_menu = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="权限管理"]')))
#     page.execute_script("arguments[0].click();", perm_menu)
#     time.sleep(0.5)
#
#     # 2. 点击子菜单【用户管理】
#     user_menu = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="用户分组"]')))
#     # JS点击，绕过元素遮挡、鼠标CDP事件风控问题
#     page.execute_script("arguments[0].click();", user_menu)
#
#     time.sleep(1)
#     global_logger.info("进入用户管理成功")
# global_logger.info("---339行-----")



def test_main() -> int:
    os.chdir(get_app_dir())
    page = get_page(port=9222)
    ok = login(page)
    return 0 if ok else 1


global_logger.info("---325行-----")
def  test_reg(page: ChromiumPage):
    global_logger.info("进入用户管理327行")
    perm_menu = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="权限管理"]')))
    page.execute_script("arguments[0].click();", perm_menu)
    time.sleep(0.5)

    # 2. 点击子菜单【用户管理】
    user_menu = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="用户分组"]')))
    # JS点击，绕过元素遮挡、鼠标CDP事件风控问题
    page.execute_script("arguments[0].click();", user_menu)

    time.sleep(1)
    global_logger.info("进入用户管理成功")
global_logger.info("---339行-----")


if __name__ == "__main__":
    sys.exit(test_main())
