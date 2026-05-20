import base64
import os
import random
import sys
import time
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 配置信息
LOGIN_URL = "http://192.168.100.110/merchant/#/login?redirect=/home/home-child"
ACCOUNT = "18521783088"
PASSWORD = "123456"

# 选择器
SEL_ACCOUNT = ".login-form .el-form-item:nth-of-type(1) input.el-input__inner"
SEL_PASSWORD = ".login-form .el-form-item:nth-of-type(2) input.el-input__inner"
SEL_LOGIN_BTN = "button.login-btn"
SEL_CAPTCHA = "#slideVerify"
SEL_SLIDER = ".slide-verify-slider-mask-item"
SEL_REFRESH = ".slide-verify-refresh-icon"

MAX_RETRY = 6


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_driver() -> webdriver.Chrome:
    """初始化并返回 Chrome 浏览器驱动"""
    user_data_dir = get_app_dir() / "browser_data"
    user_data_dir.mkdir(exist_ok=True)
    
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(options=options)
    return driver


def decode_image(data_url: str) -> np.ndarray:
    """解码 base64 图像数据为 OpenCV 数组"""
    base64_data = data_url.split(",")[1]
    image_data = base64.b64decode(base64_data)
    image = Image.open(BytesIO(image_data)).convert("RGBA")
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)


def find_gap(driver: webdriver.Chrome) -> int:
    """查找滑块缺口位置"""
    # 获取验证码画布
    js = """
    const canvas = document.querySelectorAll('#slideVerify canvas');
    if (canvas.length < 2) return null;
    return {
        bg: canvas[0].toDataURL('image/png'),
        block: canvas[1].toDataURL('image/png')
    };
    """
    
    data = driver.execute_script(js)
    if not data:
        raise Exception("无法获取验证码画布")
    
    # 解码图像
    bg_image = decode_image(data["bg"])
    block_image = decode_image(data["block"])
    
    # 保存原始图像用于调试
    debug_dir = get_app_dir() / "debug"
    debug_dir.mkdir(exist_ok=True)
    cv2.imwrite(str(debug_dir / "bg_original.png"), bg_image)
    cv2.imwrite(str(debug_dir / "block_original.png"), block_image)
    
    # 提取滑块形状
    block_gray = block_image[:, :, 3]  # Alpha通道
    
    # 二值化处理
    _, block_binary = cv2.threshold(block_gray, 127, 255, cv2.THRESH_BINARY)
    
    # 提取轮廓
    block_contour, _ = cv2.findContours(
        block_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    
    if not block_contour:
        raise Exception("无法提取滑块形状")
    
    # 找到最大轮廓（滑块）
    max_contour = max(block_contour, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(max_contour)
    block_template = block_binary[y:y+h, x:x+w]
    
    # 保存模板用于调试
    cv2.imwrite(str(debug_dir / "block_template.png"), block_template)
    
    # 处理背景图像
    bg_gray = cv2.cvtColor(bg_image, cv2.COLOR_BGRA2GRAY)
    
    # 尝试多种图像处理方法，增加更多参数组合
    methods = [
        ("canny_30_120", cv2.Canny(bg_gray, 30, 120)),
        ("canny_50_150", cv2.Canny(bg_gray, 50, 150)),
        ("canny_20_100", cv2.Canny(bg_gray, 20, 100)),
        ("threshold_100", cv2.threshold(bg_gray, 100, 255, cv2.THRESH_BINARY)[1]),
        ("threshold_120", cv2.threshold(bg_gray, 120, 255, cv2.THRESH_BINARY)[1]),
        ("blur_canny_30_120", cv2.Canny(cv2.GaussianBlur(bg_gray, (3, 3), 0), 30, 120)),
        ("blur_canny_50_150", cv2.Canny(cv2.GaussianBlur(bg_gray, (3, 3), 0), 50, 150)),
        ("adaptive_threshold_11_2", cv2.adaptiveThreshold(bg_gray, 255, 
                                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                     cv2.THRESH_BINARY, 11, 2)),
        ("adaptive_threshold_15_3", cv2.adaptiveThreshold(bg_gray, 255, 
                                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                     cv2.THRESH_BINARY, 15, 3))
    ]
    
    best_match = None
    best_score = 0
    
    # 尝试多种模板匹配方法
    match_methods = [
        ("TM_CCOEFF_NORMED", cv2.TM_CCOEFF_NORMED),
        ("TM_CCORR_NORMED", cv2.TM_CCORR_NORMED),
        ("TM_SQDIFF_NORMED", cv2.TM_SQDIFF_NORMED)  # 注意：这个方法值越小越好
    ]
    
    for method_name, processed_img in methods:
        # 保存处理后的图像用于调试
        cv2.imwrite(str(debug_dir / f"bg_{method_name}.png"), processed_img)
        
        for match_name, match_method in match_methods:
            try:
                result = cv2.matchTemplate(processed_img, block_template, match_method)
                if match_method == cv2.TM_SQDIFF_NORMED:
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    score = 1 - min_val  # 转换为值越大越好
                    current_loc = min_loc
                else:
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    score = max_val
                    current_loc = max_loc
                
                print(f"{method_name} + {match_name}: 匹配度 = {score:.4f}")
                
                if score > best_score:
                    best_score = score
                    best_match = current_loc
                    best_method = f"{method_name} + {match_name}"
            except Exception as e:
                print(f"匹配失败 {method_name} + {match_name}: {e}")
                continue
    
    # 检查是否找到有效匹配
    if best_match is None:
        raise Exception("所有匹配方法都失败")
    
    # 降低匹配阈值，提高成功率
    if best_score < 0.3:
        print(f"警告：匹配度较低 ({best_score:.4f})，可能会导致验证失败")
    
    print(f"最佳匹配方法: {best_method}, 匹配度: {best_score:.4f}")
    
    # 计算实际需要滑动的距离
    gap_x = best_match[0] - x
    
    # 智能距离调整
    # 根据匹配度动态调整校准因子
    if best_score > 0.8:
        # 高匹配度，使用较小的调整
        calibration_factor = 1.0 + random.uniform(0.01, 0.03)
    elif best_score > 0.5:
        # 中等匹配度，使用中等调整
        calibration_factor = 1.0 + random.uniform(0.02, 0.05)
    else:
        # 低匹配度，使用较大的调整
        calibration_factor = 1.0 + random.uniform(0.03, 0.08)
    
    adjusted_gap_x = int(round(gap_x * calibration_factor))
    
    # 添加随机微调，进一步提高成功率
    final_adjustment = random.uniform(0.5, 2.5)
    adjusted_gap_x = int(round(adjusted_gap_x + final_adjustment))
    
    print(f"计算得到的滑动距离: {gap_x}, 校准后: {int(round(gap_x * calibration_factor))}, 最终调整: {adjusted_gap_x}")
    
    # 确保距离为正数
    adjusted_gap_x = max(1, adjusted_gap_x)
    
    return adjusted_gap_x


def generate_human_like_path(distance: int) -> list:
    """生成更接近人类的滑动路径"""
    path = []
    
    # 总滑动时间（人类通常需要0.8-1.5秒完成滑动）
    total_time = random.uniform(0.8, 1.5)
    
    # 步骤数
    steps = random.randint(20, 30)
    step_time = total_time / steps
    
    # 加速度曲线（先加速后减速）
    for i in range(steps):
        # 使用正弦函数模拟加速度变化
        # 0-40%: 加速
        # 40-80%: 匀速
        # 80-100%: 减速
        progress = i / steps
        if progress < 0.4:
            # 加速阶段
            speed = progress / 0.4
        elif progress < 0.8:
            # 匀速阶段
            speed = 1.0
        else:
            # 减速阶段
            speed = (1.0 - (progress - 0.8) / 0.2)
        
        # 计算当前步长
        step_distance = (distance / steps) * speed
        
        # 添加随机波动
        step_distance += random.uniform(-1, 1)
        
        # 计算累计距离
        if i == 0:
            current_distance = step_distance
        else:
            current_distance = path[-1][0] + step_distance
        
        # 确保不超过目标距离
        if current_distance > distance:
            current_distance = distance
        
        # 添加到路径
        path.append((current_distance, step_time))
    
    # 可能的微调
    if random.random() > 0.6:
        # 轻微过冲
        overshoot = random.uniform(1, 3)
        path.append((distance + overshoot, random.uniform(0.05, 0.1)))
        # 回调到正确位置
        path.append((distance, random.uniform(0.05, 0.1)))
    
    return path


def human_like_slide(driver: webdriver.Chrome, slider: WebElement, distance: int) -> None:
    """使用更接近人类的方式执行滑块滑动"""
    # 获取滑块位置
    slider_rect = slider.rect
    start_x = slider_rect["x"] + slider_rect["width"] / 2
    start_y = slider_rect["y"] + slider_rect["height"] / 2
    
    # 计算结束位置
    end_x = start_x + distance
    end_y = start_y
    
    # 人类滑动的典型时间范围
    total_duration = random.uniform(0.8, 1.5)
    
    # 生成更自然的轨迹点
    def generate_natural_points(start, end, duration, steps=20):
        points = []
        for i in range(steps + 1):
            t = i / steps
            # 使用正弦函数模拟加速度变化
            acceleration = 1 - abs(2 * t - 1)
            # 计算当前位置
            current_x = start + (end - start) * t
            # 添加随机波动
            current_x += random.uniform(-1.5, 1.5)
            current_y = start_y + random.uniform(-2, 2)
            # 计算当前时间
            current_time = duration * t
            points.append((current_x, current_y, current_time))
        return points
    
    # 生成轨迹
    points = generate_natural_points(start_x, end_x, total_duration)
    
    # 使用CDP执行鼠标操作
    try:
        # 移动到滑块上方（模拟鼠标从远处移动过来）
        driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseMoved',
            'x': start_x + random.uniform(-50, 50),
            'y': start_y - random.uniform(20, 50),
            'button': 'left',
            'buttons': 0,
            'pointerType': 'mouse'
        })
        
        time.sleep(random.uniform(0.2, 0.5))
        
        # 移动到滑块中心
        for i in range(3):
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': start_x + random.uniform(-10, 10),
                'y': start_y + random.uniform(-10, 10),
                'button': 'left',
                'buttons': 0,
                'pointerType': 'mouse'
            })
            time.sleep(random.uniform(0.05, 0.1))
        
        # 最终定位到滑块中心
        driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseMoved',
            'x': start_x,
            'y': start_y,
            'button': 'left',
            'buttons': 0,
            'pointerType': 'mouse'
        })
        
        time.sleep(random.uniform(0.1, 0.3))
        
        # 按下鼠标（模拟人类按下时的微小抖动）
        for i in range(2):
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mousePressed',
                'x': start_x + random.uniform(-1, 1),
                'y': start_y + random.uniform(-1, 1),
                'button': 'left',
                'buttons': 1,
                'pointerType': 'mouse'
            })
            time.sleep(0.01)
        
        # 执行滑动轨迹
        last_time = 0
        for x, y, current_time in points:
            # 计算需要等待的时间
            wait_time = current_time - last_time
            if wait_time > 0:
                time.sleep(wait_time)
            
            # 发送鼠标移动事件
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': x,
                'y': y,
                'button': 'left',
                'buttons': 1,
                'pointerType': 'mouse'
            })
            
            last_time = current_time
        
        # 释放鼠标（模拟人类释放时的微小抖动）
        for i in range(2):
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseReleased',
                'x': end_x + random.uniform(-1, 1),
                'y': end_y + random.uniform(-1, 1),
                'button': 'left',
                'buttons': 0,
                'pointerType': 'mouse'
            })
            time.sleep(0.01)
        
        print("人类like滑块操作执行完成")
    except Exception as e:
        print(f"人类like滑块操作失败: {e}")
        raise


def slide(driver: webdriver.Chrome, distance: int) -> None:
    """执行滑块滑动"""
    # 方法1：使用CDP模拟人类操作（增强版）
    try:
        print("尝试使用增强的人类行为CDP方法执行滑块操作")
        
        # 找到滑块元素
        slider = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SEL_SLIDER))
        )
        
        # 获取滑块位置
        slider_rect = slider.rect
        start_x = slider_rect["x"] + slider_rect["width"] / 2
        start_y = slider_rect["y"] + slider_rect["height"] / 2
        
        # 智能距离调整
        # 根据距离大小动态调整
        if distance < 100:
            # 短距离，需要更精确的调整
            adjustment = random.uniform(0.5, 1.5)
        elif distance < 200:
            # 中等距离
            adjustment = random.uniform(1.0, 2.0)
        else:
            # 长距离
            adjustment = random.uniform(1.5, 2.5)
        
        adjusted_distance = distance + adjustment
        print(f"原始距离: {distance}, 调整后: {adjusted_distance}")
        
        end_x = start_x + adjusted_distance
        end_y = start_y
        
        # 1. 模拟鼠标从页面其他地方自然移动过来
        # 随机起始位置，更符合人类操作习惯
        initial_x = start_x + random.uniform(-150, 150)
        initial_y = start_y + random.uniform(-80, -30)  # 从上方移动下来
        
        driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseMoved',
            'x': initial_x,
            'y': initial_y,
            'button': 'left',
            'buttons': 0,
            'pointerType': 'mouse',
            'movementX': random.uniform(-10, 10),
            'movementY': random.uniform(-5, 5)
        })
        time.sleep(random.uniform(0.4, 1.0))  # 更自然的移动时间
        
        # 2. 移动到滑块上方，添加犹豫和调整
        for _ in range(random.randint(2, 4)):
            adjustment_x = start_x + random.uniform(-20, 20)
            adjustment_y = start_y - random.uniform(10, 25)
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': adjustment_x,
                'y': adjustment_y,
                'button': 'left',
                'buttons': 0,
                'pointerType': 'mouse',
                'movementX': random.uniform(-5, 5),
                'movementY': random.uniform(-3, 3)
            })
            time.sleep(random.uniform(0.15, 0.35))
        
        # 3. 接近滑块时的精细调整，模拟人类对准目标
        for _ in range(random.randint(3, 5)):
            fine_adjust_x = start_x + random.uniform(-4, 4)
            fine_adjust_y = start_y + random.uniform(-4, 4)
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': fine_adjust_x,
                'y': fine_adjust_y,
                'button': 'left',
                'buttons': 0,
                'pointerType': 'mouse',
                'movementX': random.uniform(-2, 2),
                'movementY': random.uniform(-2, 2)
            })
            time.sleep(random.uniform(0.08, 0.2))
        
        # 4. 最终定位到滑块中心
        driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseMoved',
            'x': start_x,
            'y': start_y,
            'button': 'left',
            'buttons': 0,
            'pointerType': 'mouse'
        })
        time.sleep(random.uniform(0.2, 0.5))  # 模拟人类按下前的犹豫
        
        # 5. 按下鼠标，添加轻微的抖动和压力变化
        for _ in range(random.randint(1, 3)):
            jitter_x = start_x + random.uniform(-1, 1)
            jitter_y = start_y + random.uniform(-1, 1)
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mousePressed',
                'x': jitter_x,
                'y': jitter_y,
                'button': 'left',
                'buttons': 1,
                'pointerType': 'mouse',
                'pressure': 0.5 + random.uniform(0, 0.3)  # 模拟压力变化
            })
            time.sleep(0.01)
        
        # 6. 执行滑动 - 模拟人类的真实滑动行为
        # 人类滑动时会有加速、匀速、减速的过程，可能还有停顿和调整
        total_duration = random.uniform(1.2, 2.0)  # 人类滑动通常需要1-2秒
        steps = random.randint(20, 30)  # 更多步骤，更自然
        step_duration = total_duration / steps
        
        # 模拟人类可能的操作错误和调整
        has_adjustment = random.random() > 0.6  # 40%的概率会有调整
        adjustment_points = []
        if has_adjustment:
            # 可能有多个调整点
            adjustment_count = random.randint(1, 2)
            for _ in range(adjustment_count):
                adjustment_points.append(random.randint(5, steps - 5))
        
        # 模拟人类滑动时的手部抖动
        def generate_jitter():
            return random.uniform(-1, 1)
        
        for i in range(steps):
            # 计算当前位置
            progress = i / steps
            
            # 使用更真实的缓动函数，模拟人类的真实加速/减速
            if progress < 0.25:
                # 加速阶段
                ease_progress = 4 * progress * progress * progress
            elif progress < 0.75:
                # 匀速阶段
                ease_progress = 0.25 + 0.5 * ((progress - 0.25) / 0.5)
            else:
                # 减速阶段
                ease_progress = 0.75 + 0.25 * (1 - ((1 - (progress - 0.75) / 0.25) ** 3))
            
            # 添加随机波动，模拟人类操作的不精确性
            random_factor = random.uniform(-0.03, 0.03) * adjusted_distance
            current_x = start_x + adjusted_distance * ease_progress + random_factor
            current_y = start_y + generate_jitter() * 2  # 垂直方向的随机波动
            
            # 模拟人类可能的调整
            if has_adjustment and i in adjustment_points:
                # 短暂停顿
                time.sleep(random.uniform(0.15, 0.25))
                # 小范围调整
                for _ in range(3):
                    adjust_x = current_x + random.uniform(-3, 3)
                    adjust_y = current_y + random.uniform(-2, 2)
                    driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                        'type': 'mouseMoved',
                        'x': adjust_x,
                        'y': adjust_y,
                        'button': 'left',
                        'buttons': 1,
                        'pointerType': 'mouse',
                        'pressure': 0.6 + random.uniform(0, 0.2)
                    })
                    time.sleep(random.uniform(0.08, 0.15))
            
            # 移动鼠标
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': current_x,
                'y': current_y,
                'button': 'left',
                'buttons': 1,
                'pointerType': 'mouse',
                'movementX': random.uniform(-3, 3),
                'movementY': random.uniform(-2, 2),
                'pressure': 0.5 + random.uniform(0, 0.3)
            })
            
            # 随机的时间间隔，模拟人类操作的不规则性
            sleep_time = step_duration * random.uniform(0.7, 1.3)
            time.sleep(sleep_time)
        
        # 7. 释放鼠标前的犹豫
        time.sleep(random.uniform(0.1, 0.2))
        
        # 8. 释放鼠标，可能会有轻微的抖动
        release_x = end_x + random.uniform(-1.5, 1.5)
        release_y = end_y + random.uniform(-1.5, 1.5)
        driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
            'type': 'mouseReleased',
            'x': release_x,
            'y': release_y,
            'button': 'left',
            'buttons': 0,
            'pointerType': 'mouse',
            'pressure': 0.1  # 释放时压力减小
        })
        
        # 9. 释放后的鼠标移动
        if random.random() > 0.6:
            # 模拟鼠标自然移开
            move_away_x = end_x + random.uniform(15, 40)
            move_away_y = end_y + random.uniform(-15, 15)
            driver.execute_cdp_cmd('Input.dispatchMouseEvent', {
                'type': 'mouseMoved',
                'x': move_away_x,
                'y': move_away_y,
                'button': 'left',
                'buttons': 0,
                'pointerType': 'mouse'
            })
            time.sleep(random.uniform(0.15, 0.3))
        
        # 10. 触发额外的事件，模拟真实用户操作
        driver.execute_script("""
            var slider = arguments[0];
            
            // 触发多个事件，模拟真实用户操作
            var events = [
                new Event('mousedown', { bubbles: true, cancelable: true }),
                new Event('mousemove', { bubbles: true, cancelable: true }),
                new Event('mouseup', { bubbles: true, cancelable: true }),
                new Event('change', { bubbles: true }),
                new Event('input', { bubbles: true }),
                new Event('blur', { bubbles: true }),
                new Event('mouseleave', { bubbles: true })
            ];
            
            events.forEach(function(event) {
                slider.dispatchEvent(event);
            });
            
            // 触发滑块容器的事件
            var container = slider.parentElement;
            if (container) {
                var containerEvents = [
                    new Event('mousedown', { bubbles: true, cancelable: true }),
                    new Event('mousemove', { bubbles: true, cancelable: true }),
                    new Event('mouseup', { bubbles: true, cancelable: true })
                ];
                containerEvents.forEach(function(event) {
                    container.dispatchEvent(event);
                });
            }
            
            // 触发文档级别的事件
            var docEvents = [
                new Event('mousemove', { bubbles: true, cancelable: true }),
                new Event('mouseup', { bubbles: true, cancelable: true })
            ];
            docEvents.forEach(function(event) {
                document.dispatchEvent(event);
            });
        """, slider)
        
        print("增强的人类行为CDP滑块操作执行完成")
        time.sleep(2.5)  # 给网站更多时间处理验证
        return
    except Exception as e:
        print(f"增强的人类行为CDP操作失败: {e}")
    
    # 方法2：使用传统的ActionChains，但添加更多人类行为特征
    try:
        print("尝试使用增强的人类行为ActionChains执行滑块操作")
        
        # 找到滑块元素
        slider = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_SLIDER))
        )
        
        # 获取滑块位置
        slider_rect = slider.rect
        start_x = slider_rect["x"] + slider_rect["width"] / 2
        start_y = slider_rect["y"] + slider_rect["height"] / 2
        
        # 智能距离调整
        if distance < 100:
            adjustment = random.uniform(0.5, 1.5)
        elif distance < 200:
            adjustment = random.uniform(1.0, 2.0)
        else:
            adjustment = random.uniform(1.5, 2.5)
        
        adjusted_distance = distance + adjustment
        print(f"原始距离: {distance}, 调整后: {adjusted_distance}")
        
        # 创建ActionChains
        action = ActionChains(driver)
        
        # 模拟鼠标从远处随机位置移动过来
        initial_x = start_x + random.uniform(-200, 200)
        initial_y = start_y + random.uniform(-100, -40)
        action.move_by_offset(initial_x, initial_y)
        action.pause(random.uniform(0.5, 1.0))
        
        # 移动到滑块附近，添加犹豫和调整
        for _ in range(random.randint(3, 5)):
            adjust_x = start_x - initial_x + random.uniform(-15, 15)
            adjust_y = start_y - initial_y + random.uniform(-8, 8)
            action.move_by_offset(adjust_x, adjust_y)
            action.pause(random.uniform(0.15, 0.35))
            initial_x = start_x + random.uniform(-15, 15)
            initial_y = start_y + random.uniform(-8, 8)
        
        # 移动到滑块上
        action.move_to_element(slider)
        action.pause(random.uniform(0.3, 0.6))  # 模拟按下前的犹豫
        
        # 微小调整，模拟人类对准目标
        for _ in range(random.randint(3, 4)):
            action.move_by_offset(random.uniform(-1.5, 1.5), random.uniform(-1.5, 1.5))
            action.pause(random.uniform(0.08, 0.15))
        
        # 按下鼠标
        action.click_and_hold()
        action.pause(random.uniform(0.15, 0.35))
        
        # 执行滑动，添加随机波动和调整
        total_offset = 0
        step = 1.5  # 更小的步长，更接近人类操作
        has_adjustment = random.random() > 0.5
        adjustment_made = False
        
        while total_offset < adjusted_distance:
            current_step = min(step, adjusted_distance - total_offset)
            # 随机垂直偏移，幅度更大
            y_offset = random.uniform(-1.5, 1.5)
            action.move_by_offset(current_step, y_offset)
            
            # 模拟人类的不规则操作速度
            action.pause(random.uniform(0.05, 0.12))
            total_offset += current_step
            
            # 随机调整
            if has_adjustment and not adjustment_made and total_offset > adjusted_distance * 0.2 and total_offset < adjusted_distance * 0.8:
                # 小范围调整
                action.move_by_offset(random.uniform(-3, 3), random.uniform(-2, 2))
                action.pause(random.uniform(0.15, 0.25))
                action.move_by_offset(random.uniform(-2, 2), random.uniform(-1, 1))
                action.pause(random.uniform(0.08, 0.15))
                adjustment_made = True
        
        # 可能的过冲和回调
        if random.random() > 0.6:
            overshoot = random.uniform(1.5, 3.5)
            action.move_by_offset(overshoot, random.uniform(-0.8, 0.8))
            action.pause(random.uniform(0.08, 0.15))
            action.move_by_offset(-overshoot, random.uniform(-0.8, 0.8))
            action.pause(random.uniform(0.08, 0.15))
        
        # 释放鼠标前的犹豫
        action.pause(random.uniform(0.1, 0.2))
        
        # 释放鼠标
        action.release()
        
        # 释放后的鼠标移动
        if random.random() > 0.6:
            action.move_by_offset(random.uniform(15, 30), random.uniform(-8, 8))
            action.pause(random.uniform(0.15, 0.3))
        
        # 执行所有操作
        action.perform()
        
        print("增强的人类行为ActionChains滑块操作执行完成")
        time.sleep(2.5)
        return
    except Exception as e:
        print(f"增强的人类行为ActionChains执行失败: {e}")
    
    # 所有方法都失败
    raise Exception("所有滑块操作方法都失败")


def refresh_captcha(driver: webdriver.Chrome) -> None:
    """刷新验证码"""
    try:
        refresh_btn = driver.find_element(By.CSS_SELECTOR, SEL_REFRESH)
        refresh_btn.click()
        time.sleep(1)
    except Exception as e:
        print(f"刷新验证码失败: {e}")


def is_captcha_solved(driver: webdriver.Chrome) -> bool:
    """检查验证码是否解决"""
    try:
        captcha = driver.find_element(By.CSS_SELECTOR, SEL_CAPTCHA)
        return not captcha.is_displayed()
    except:
        return True


def solve_captcha(driver: webdriver.Chrome) -> bool:
    """解决验证码"""
    for attempt in range(MAX_RETRY):
        try:
            # 等待验证码加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SEL_CAPTCHA))
            )
            time.sleep(1)
            
            # 计算滑动距离
            distance = find_gap(driver)
            print(f"第 {attempt + 1} 次尝试，滑动距离: {distance}")
            
            # 执行滑动
            slide(driver, distance)
            time.sleep(2)
            
            # 检查是否成功
            if is_captcha_solved(driver):
                print("验证码验证成功")
                return True
            else:
                print(f"第 {attempt + 1} 次验证失败，刷新验证码")
                refresh_captcha(driver)
                
        except Exception as e:
            print(f"验证码处理失败: {e}")
            refresh_captcha(driver)
            continue
    
    return False


def login(driver: webdriver.Chrome) -> bool:
    """登录流程"""
    print(f"打开登录页面: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    
    # 等待页面完全加载
    time.sleep(3)


    # 检查是否存在iframe
    try:
        iframes = driver.find_elements(By.TAG_NAME, 'iframe')
        if iframes:
            print(f"发现 {len(iframes)} 个iframe，尝试切换到第一个")
            driver.switch_to.frame(iframes[0])
    except Exception as e:
        print(f"检查iframe时出错: {e}")
    
    # 输入账号密码
    try:
        # 等待账号输入框可见且可交互

        print("等待账号输入框...")
        account_input = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_ACCOUNT))
        )
        print("找到账号输入框")
        
        # 等待密码输入框可见且可交互
        print("等待密码输入框...")
        password_input = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_PASSWORD))
        )
        print("找到密码输入框")
        
        # 输入账号
        try:
            account_input.clear()
            time.sleep(0.5)
            account_input.send_keys(ACCOUNT)
            print(f"已输入账号: {ACCOUNT}")
        except Exception as e:
            print(f"输入账号失败: {e}")
            # 尝试使用JavaScript输入
            driver.execute_script("arguments[0].value = arguments[1]", account_input, ACCOUNT)
            print("已使用JavaScript输入账号")
        
        # 输入密码
        try:
            password_input.clear()
            time.sleep(0.5)
            password_input.send_keys(PASSWORD)
            print(f"已输入密码")
        except Exception as e:
            print(f"输入密码失败: {e}")
            # 尝试使用JavaScript输入
            driver.execute_script("arguments[0].value = arguments[1]", password_input, PASSWORD)
            print("已使用JavaScript输入密码")
        
        # 点击登录
        print("等待登录按钮...")
        login_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_LOGIN_BTN))
        )
        print("找到登录按钮")
        
        try:
            login_btn.click()
            print("已点击登录按钮")
        except Exception as e:
            print(f"点击登录按钮失败: {e}")
            # 尝试使用JavaScript点击
            driver.execute_script("arguments[0].click();", login_btn)
            print("已使用JavaScript点击登录按钮")
        
    except Exception as e:
        print(f"登录信息填写失败: {e}")
        # 截图保存以便调试
        screenshot_path = get_app_dir() / "login_error.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"已保存错误截图到: {screenshot_path}")
        return False
    
    # 处理验证码
    try:
        # 等待验证码出现
        captcha_present = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SEL_CAPTCHA))
        )
        
        if captcha_present:
            print("检测到验证码，开始处理")
            if not solve_captcha(driver):
                print("验证码处理失败")
                return False
        else:
            print("未检测到验证码")
            
    except Exception as e:
        print(f"验证码检测失败: {e}")
    
    # 检查登录状态
    time.sleep(3)
    if "/login" not in driver.current_url:
        print(f"登录成功，当前URL: {driver.current_url}")
        return True
    else:
        print(f"登录失败，当前URL: {driver.current_url}")
        return False


def main() -> None:
    """主函数"""
    os.chdir(get_app_dir())
    
    driver = None
    try:
        driver = get_driver()
        success = login(driver)
        print(f"\n登录{'成功' if success else '失败'}")
        # 保持浏览器打开
        print("浏览器保持打开状态，按回车键退出...")
        input()
    except Exception as e:
        print(f"程序执行失败: {e}")
        # 保持浏览器打开
        print("浏览器保持打开状态，按回车键退出...")
        input()
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()