import logging
import os
import random
import re
import time
import cv2
import ddddocr
import requests
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def init_selenium() -> WebDriver:
    ops = Options()
    ops.add_argument("--no-sandbox")
    ops.add_argument("--disable-dev-shm-usage")
    ops.add_argument("--disable-blink-features=AutomationControlled")
    ops.add_experimental_option("excludeSwitches", ["enable-automation"])
    ops.add_experimental_option('useAutomationExtension', False)
    
    if debug:
        ops.add_experimental_option("detach", True)
    if linux:
        ops.add_argument("--headless")
        ops.add_argument("--disable-gpu")
        ops.add_argument("--disable-extensions")
        ops.add_argument("--disable-plugins-discovery")
        ops.add_argument("--disable-background-timer-throttling")
        ops.add_argument("--disable-renderer-backgrounding")
        ops.add_argument("--disable-backgrounding-occluded-windows")
        # 添加容器环境支持参数
        ops.add_argument("--disable-dev-shm-usage")
        ops.add_argument("--no-sandbox")
        ops.add_argument("--disable-gpu")
        ops.add_argument("--remote-debugging-port=9222")
        ops.add_argument("--disable-extensions")
        ops.add_argument("--disable-setuid-sandbox")
        ops.add_argument("--disable-web-security")
        ops.add_argument("--allow-running-insecure-content")
        ops.add_argument("--no-first-run")
        ops.add_argument("--no-default-browser-check")
        ops.add_argument("--disable-features=VizDisplayCompositor")
        ops.add_argument("--disable-ipc-flooding-protection")
        return webdriver.Chrome(service=Service("./chromedriver"), options=ops)
    return webdriver.Chrome(service=Service("chromedriver.exe"), options=ops)


def download_image(url, filename):
    os.makedirs("temp", exist_ok=True)
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        path = os.path.join("temp", filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    else:
        logger.error("下载图片失败！")
        return False


def get_url_from_style(style):
    return re.search(r'url\(["\']?(.*?)["\']?\)', style).group(1)


def get_width_from_style(style):
    return re.search(r'width:\s*([\d.]+)px', style).group(1)


def get_height_from_style(style):
    return re.search(r'height:\s*([\d.]+)px', style).group(1)


def process_captcha():
    try:
        download_captcha_img()
        if check_captcha():
            logger.info("开始识别验证码")
            captcha = cv2.imread("temp/captcha.jpg")
            with open("temp/captcha.jpg", 'rb') as f:
                captcha_b = f.read()
            bboxes = det.detection(captcha_b)
            result = dict()
            for i in range(len(bboxes)):
                x1, y1, x2, y2 = bboxes[i]
                spec = captcha[y1:y2, x1:x2]
                cv2.imwrite(f"temp/spec_{i + 1}.jpg", spec)
                for j in range(3):
                    similarity, matched = compute_similarity(f"temp/sprite_{j + 1}.jpg", f"temp/spec_{i + 1}.jpg")
                    similarity_key = f"sprite_{j + 1}.similarity"
                    position_key = f"sprite_{j + 1}.position"
                    if similarity_key in result.keys():
                        if float(result[similarity_key]) < similarity:
                            result[similarity_key] = similarity
                            result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
                    else:
                        result[similarity_key] = similarity
                        result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
            if check_answer(result):
                for i in range(3):
                    similarity_key = f"sprite_{i + 1}.similarity"
                    position_key = f"sprite_{i + 1}.position"
                    positon = result[position_key]
                    logger.info(f"图案 {i + 1} 位于 ({positon})，匹配率：{result[similarity_key]}")
                    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
                    style = slideBg.get_attribute("style")
                    x, y = int(positon.split(",")[0]), int(positon.split(",")[1])
                    width_raw, height_raw = captcha.shape[1], captcha.shape[0]
                    width, height = float(get_width_from_style(style)), float(get_height_from_style(style))
                    x_offset, y_offset = float(-width / 2), float(-height / 2)
                    final_x, final_y = int(x_offset + x / width_raw * width), int(y_offset + y / height_raw * height)
                    ActionChains(driver).move_to_element_with_offset(slideBg, final_x, final_y).click().perform()
                confirm = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="tcStatus"]/div[2]/div[2]/div/div')))
                logger.info("提交验证码")
                confirm.click()
                time.sleep(5)
                result = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
                if result.get_attribute("class") == 'tc-opera pointer show-success':
                    logger.info("验证码通过")
                    return
                else:
                    logger.error("验证码未通过，正在重试")
            else:
                logger.error("验证码识别失败，正在重试")
        else:
            logger.error("当前验证码识别率低，尝试刷新")
        reload = driver.find_element(By.XPATH, '//*[@id="reload"]')
        time.sleep(5)
        reload.click()
        time.sleep(5)
        process_captcha()
    except TimeoutException:
        logger.error("获取验证码图片失败")


def download_captcha_img():
    if os.path.exists("temp"):
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
    img1_style = slideBg.get_attribute("style")
    img1_url = get_url_from_style(img1_style)
    logger.info("开始下载验证码图片(1): " + img1_url)
    download_image(img1_url, "captcha.jpg")
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    download_image(img2_url, "sprite.jpg")


def check_captcha() -> bool:
    raw = cv2.imread("temp/sprite.jpg")
    for i in range(3):
        w = raw.shape[1]
        temp = raw[:, w // 3 * i: w // 3 * (i + 1)]
        cv2.imwrite(f"temp/sprite_{i + 1}.jpg", temp)
        with open(f"temp/sprite_{i + 1}.jpg", mode="rb") as f:
            temp_rb = f.read()
        if ocr.classification(temp_rb) in ["0", "1"]:
            return False
    return True


# 检查是否存在重复坐标，快速判断识别错误
def check_answer(d: dict) -> bool:
    flipped = dict()
    for key in d.keys():
        flipped[d[key]] = key
    return len(d.values()) == len(flipped.keys())


def compute_similarity(img1_path, img2_path):
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        return 0.0, 0

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good = [m for m_n in matches if len(m_n) == 2 for m, n in [m_n] if m.distance < 0.8 * n.distance]

    if len(good) == 0:
        return 0.0, 0

    similarity = len(good) / len(matches)
    return similarity, len(good)


if __name__ == "__main__":
    # 连接超时等待
    timeout = 30
    # 最大随机等待延时
    max_delay = 90
    user = os.environ.get('USER', 'username')
    pwd = os.environ.get('PASSWORD', '12345678')
    
    if user == 'username' or pwd == '12345678':
        logging.warning("警告：正在使用默认的用户名或密码，请在环境变量中设置 USER 和 PASSWORD！")
    debug = True
    linux = True

    # 以下为代码执行区域，请勿修改！
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    ver = "2.2"
    logger.info("------------------------------------------------------------------")
    logger.info(f"雨云签到工具 v{ver} by SerendipityR ~")
    logger.info("Github发布页: https://github.com/SerendipityR-2022/Rainyun-Qiandao")
    logger.info("------------------------------------------------------------------")

    logger.info("------------------项目为二开容器化运行原作者在上面-------------------")
    logger.info("                         VQ同号: 14768070                         ")
    logger.info("                         交流Q群: 5036150                         ")
    logger.info("               本项目仅作为学习参考，请勿用于其他用途                ")
    logger.info("------------------------------------------------------------------")
    delay = random.randint(0, max_delay)
    delay_sec = random.randint(0, 60)
    if not debug:
        logger.info(f"随机延时等待 {delay} 分钟 {delay_sec} 秒")
        time.sleep(delay * 60 + delay_sec)
    logger.info("初始化 ddddocr")
    ocr = ddddocr.DdddOcr(ocr=True, show_ad=False)
    det = ddddocr.DdddOcr(det=True, show_ad=False)
    logger.info("初始化 Selenium")
    driver = init_selenium()
    # 过 Selenium 检测
    with open("stealth.min.js", mode="r") as f:
        js = f.read()
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": js
    })
    logger.info("发起登录请求")
    driver.get("https://app.rainyun.com/auth/login")
    wait = WebDriverWait(driver, timeout)
    try:
        wait.until(EC.title_contains("雨云"))
        logger.info("页面标题已加载: {}".format(driver.title))
        time.sleep(10)
        logger.info("等待登录表单元素加载...")
        try:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
            logger.info("检测到输入框元素")
        except TimeoutException:
            logger.warning("未检测到输入框，继续尝试...")
        time.sleep(5)
        logger.info("正在查找登录表单元素...")
        username = None
        username_selectors = [
            (By.NAME, 'login-field'),
            (By.CSS_SELECTOR, 'input[name="login-field"]'),
            (By.CSS_SELECTOR, 'input[type="text"][name*="user" i]'),
            (By.CSS_SELECTOR, 'input[type="text"][placeholder*="用户名" i], input[type="text"][placeholder*="username" i]'),
            (By.XPATH, '//input[@name="login-field"]'),
            (By.XPATH, '//input[contains(@placeholder, "用户名") or contains(@placeholder, "username") or contains(@type, "text")][@type="text"]'),
            (By.CSS_SELECTOR, 'input[placeholder*="账号" i], input[placeholder*="手机号" i], input[placeholder*="邮箱" i]'),
            (By.CSS_SELECTOR, 'input[data-testid="username" i], input[data-test="username" i]'),
            (By.CSS_SELECTOR, '.login-field input, .username-input, .user-input'),
            (By.XPATH, '//input[contains(@class, "login") and @type="text"]'),
            (By.XPATH, '//input[contains(@class, "user") and @type="text"]'),
            (By.XPATH, '//input[contains(@id, "user") or contains(@id, "login")]')
        ]
        
        for selector in username_selectors:
            try:
                username = wait.until(EC.visibility_of_element_located(selector))
                logger.info(f"找到用户名输入框: {selector}")
                break
            except TimeoutException:
                continue
        
        if username is None:
            logger.error("无法找到用户名输入框")
            logger.info("页面源码:")
            logger.info(driver.page_source[:3000])
            exit()
        
        password = None
        password_selectors = [
            (By.NAME, 'login-password'),
            (By.CSS_SELECTOR, 'input[name="login-password"]'),
            (By.CSS_SELECTOR, 'input[type="password"][name*="pass" i]'),
            (By.CSS_SELECTOR, 'input[type="password"][placeholder*="密码" i], input[type="password"][placeholder*="password" i]'),
            (By.XPATH, '//input[@name="login-password"]'),
            (By.XPATH, '//input[contains(@placeholder, "密码") or contains(@placeholder, "password")][@type="password"]'),
            (By.CSS_SELECTOR, 'input[type="password"][placeholder*="密码" i]'),
            (By.CSS_SELECTOR, 'input[data-testid="password" i], input[data-test="password" i]'),
            (By.CSS_SELECTOR, '.password-input, .pwd-input'),
            (By.XPATH, '//input[contains(@class, "password") and @type="password"]'),
            (By.XPATH, '//input[contains(@class, "pwd") and @type="password"]'),
            (By.XPATH, '//input[contains(@id, "pass") or contains(@id, "pwd")]')
        ]
        
        for selector in password_selectors:
            try:
                password = wait.until(EC.visibility_of_element_located(selector))
                logger.info(f"找到密码输入框: {selector}")
                break
            except TimeoutException:
                continue
        
        if password is None:
            logger.error("无法找到密码输入框")
            logger.info("页面源码:")
            logger.info(driver.page_source[:3000])
        login_button = None
        login_selectors = [
            (By.XPATH, '//*[@id="app"]/div[1]/div[1]/div/div[2]/fade/div/div/span/form/button'),
            (By.XPATH, '//button[@type="submit"]'),
            (By.XPATH, '//form//button[contains(@class, "login") or contains(@class, "submit") or contains(@class, "button")]'),
            (By.XPATH, '//button[contains(text(), "登录") or contains(text(), "登录") or contains(text(), "Login")]'),
            (By.CSS_SELECTOR, 'button[type="submit"]'),
            (By.CSS_SELECTOR, 'input[type="submit"]'),
            (By.CSS_SELECTOR, 'button[class*="login" i], button[class*="submit" i], button[class*="button" i]'),
            (By.CSS_SELECTOR, 'button[data-testid="login" i], button[data-test="login" i]'),
            (By.CSS_SELECTOR, '.login-button, .submit-btn, .auth-button'),
            (By.XPATH, '//button[contains(@class, "login") or contains(@class, "submit") or contains(@class, "button")]'),
            (By.XPATH, '//span[contains(text(), "登录")]/parent::button'),
            (By.XPATH, '//div[contains(@class, "login")]/button')
        ]
        
        for selector in login_selectors:
            try:
                login_button = wait.until(EC.element_to_be_clickable(selector))
                logger.info(f"找到登录按钮: {selector}")
                break
            except TimeoutException:
                logger.debug(f"未找到登录按钮: {selector}")
                continue
        
        if login_button is None:
            logger.error("无法找到登录按钮")
            logger.info("页面源码:")
            logger.info(driver.page_source[:2000])
            exit()
        
        logger.info("正在输入用户名和密码...")
        username.send_keys(user)
        password.send_keys(pwd)
        logger.info("正在点击登录按钮...")
        login_button.click()
        
        # 等待页面跳转或响应
        time.sleep(3)
        logger.info(f"当前页面URL: {driver.current_url}")
        logger.info(f"页面标题: {driver.title}")
        
    except TimeoutException:
        logger.error("页面加载超时，请尝试延长超时时间或切换到国内网络环境！")
        logger.info(f"当前页面URL: {driver.current_url}")
        logger.info(f"页面标题: {driver.title}")
        logger.info("页面源码:")
        logger.info(driver.page_source[:2000])
        exit()
    try:
        login_captcha = wait.until(EC.visibility_of_element_located((By.ID, 'tcaptcha_iframe_dy')))
        logger.warning("触发验证码！")
        driver.switch_to.frame("tcaptcha_iframe_dy")
        process_captcha()
    except TimeoutException:
        logger.info("未触发验证码")
    time.sleep(5)
    driver.switch_to.default_content()
    if driver.current_url == "https://app.rainyun.com/dashboard":
        logger.info("登录成功！")
        logger.info("正在转到赚取积分页")
        driver.get("https://app.rainyun.com/account/reward/earn")
        driver.implicitly_wait(5)
        earn = driver.find_element(By.XPATH,
                                   '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[2]/div/div/div/div[1]/div/div[1]/div/div[1]/div/span[2]/a')
        logger.info("点击赚取积分")
        earn.click()
        logger.info("处理验证码")
        driver.switch_to.frame("tcaptcha_iframe_dy")
        process_captcha()
        driver.switch_to.default_content()
        driver.implicitly_wait(5)
        points_raw = driver.find_element(By.XPATH,
                                         '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3').get_attribute(
            "textContent")
        current_points = int(''.join(re.findall(r'\d+', points_raw)))
        logger.info(f"当前剩余积分: {current_points} | 约为 {current_points / 2000:.2f} 元")
        logger.info("任务执行成功！")
    else:
        logger.error("登录失败！")
