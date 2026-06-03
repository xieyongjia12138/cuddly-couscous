import os
import sys
import base64
import io
import time
import mimetypes
import urllib.request
import urllib.error
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image

# ==========================================
# 配置部分
# ==========================================
# 设置默认的目标 URL
DEFAULT_URL = 'https://connect.huaweicloud.com/courses/learn/learning/sp:cloudEdu_?courseNo=course-v1:HuaweiX+CBUCNXK068+Self-paced&courseType=1&source=1'

def get_user_choice():
    """
    交互式获取用户参数选择
    """
    print("="*50)
    print("🔧 爬虫参数配置")
    print("="*50)
    
    # 1. 获取 URL
    url_input = input(f"请输入目标 URL (直接回车使用默认值):\n[{DEFAULT_URL}]\n> ")
    target_url = url_input.strip() or DEFAULT_URL

    # 2. 选择运行模式
    while True:
        headless_input = input("\n选择浏览器运行模式:\n1. 正常模式 (可见浏览器)\n2. 无头模式 (后台运行，推荐)\n请选择 (1/2, 默认 2): ")
        use_headless = True
        if headless_input == "1":
            use_headless = False
            break
        elif headless_input == "2" or headless_input == "":
            use_headless = True
            break
        else:
            print("请输入 1 或 2")

    # 3. 选择是否等待手动登录
    while True:
        login_input = input("\n是否需要手动登录?\n1. 是 (打开浏览器，你登录后按回车继续)\n2. 否 (自动运行)\n请选择 (1/2, 默认 2): ")
        wait_for_login = False
        if login_input == "1":
            wait_for_login = True
            break
        elif login_input == "2" or login_input == "":
            wait_for_login = False
            break
        else:
            print("请输入 1 或 2")

    # 4. 选择保存内容类型
    while True:
        content_input = input("\n选择要保存的内容:\n1. 全部内容 (HTML, 截图, 图片, Canvas)\n2. 仅 Canvas (只保存画布内容)\n请选择 (1/2, 默认 1): ")
        only_canvas = False
        if content_input == "2":
            only_canvas = True
            break
        elif content_input == "1" or content_input == "":
            only_canvas = False
            break
        else:
            print("请输入 1 或 2")

    # 5. 设置输出目录
    output_dir = input(f"\n请输入输出目录 (默认为 'output'): ") or "output"

    return {
        "url": target_url,
        "headless": use_headless,
        "wait_for_login": wait_for_login,
        "only_canvas": only_canvas,
        "output": output_dir
    }

def main():
    # 获取用户配置
    config = get_user_choice()
    
    print("\n" + "="*50)
    print("🚀 开始运行爬虫...")
    print("="*50)
    print(f"目标地址: {config['url']}")
    print(f"运行模式: {'无头模式' if config['headless'] else '正常模式'}")
    print(f"等待登录: {'是' if config['wait_for_login'] else '否'}")
    print(f"保存内容: {'仅 Canvas' if config['only_canvas'] else '全部内容'}")
    print(f"输出目录: {config['output']}")
    print("-"*50)

    # 创建输出目录
    os.makedirs(config['output'], exist_ok=True)

    # 配置 Chrome 选项
    chrome_options = Options()
    
    if config['headless']:
        chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    # 增加用户代理，减少被检测为自动化工具的概率
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print('打开页面：', config['url'])
        driver.get(config['url'])

        # 如果需要手动登录
        if config['wait_for_login']:
            print('\n⚠️ 浏览器已打开，请在浏览器中完成登录。')
            input('登录完成后，回到此处按回车键继续...')
        
        # 等待页面加载
        driver.implicitly_wait(5)
        time.sleep(2)

        # 1. 保存页面 HTML
        if not config['only_canvas']:
            html_path = os.path.join(config['output'], 'page.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print('✅ 保存页面 HTML =>', html_path)

        # 2. 保存屏幕截图
        if not config['only_canvas']:
            screenshot_path = os.path.join(config['output'], 'screenshot.png')
            driver.save_screenshot(screenshot_path)
            print('✅ 保存截图 =>', screenshot_path)

        # 3. 滚动页面以触发懒加载
        print('🔄 正在滚动页面以加载内容...')
        try:
            total_height = driver.execute_script('return document.body.scrollHeight') or 0
        except Exception:
            total_height = 0
            
        scroll_pos = 0
        while scroll_pos < total_height:
            scroll_pos += 800
            try:
                driver.execute_script(f'window.scrollTo(0, {scroll_pos});')
            except Exception:
                pass
            time.sleep(0.5)
            
            try:
                total_height = driver.execute_script('return document.body.scrollHeight') or total_height
            except Exception:
                break

        # 4. 提取 Canvas 内容 (主文档和 iframe)
        canvas_dataurls = []
        
        # 提取主文档 Canvas
        try:
            count = driver.execute_script("return document.querySelectorAll('canvas').length") or 0
            for idx in range(count):
                try:
                    data_url = driver.execute_script("return document.querySelectorAll('canvas')[arguments[0]].toDataURL('image/png');", idx)
                    if data_url:
                        canvas_dataurls.append(data_url)
                except Exception as e:
                    print(f'提取主文档 canvas {idx} 失败：', e)
        except Exception as e:
            print('查找主文档 Canvas 时出错：', e)

        # 提取 iframe 中的 Canvas
        try:
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            print(f'找到 {len(iframes)} 个 iframe，正在处理...')
            for fidx, iframe in enumerate(iframes, start=1):
                try:
                    driver.switch_to.frame(iframe)
                    fcount = driver.execute_script("return document.querySelectorAll('canvas').length") or 0
                    for idx in range(fcount):
                        try:
                            data_url = driver.execute_script("return document.querySelectorAll('canvas')[arguments[0]].toDataURL('image/png');", idx)
                            if data_url:
                                canvas_dataurls.append(data_url)
                        except Exception as e:
                            print(f'提取 iframe_{fidx} canvas {idx} 失败：', e)
                except Exception as e:
                    print(f'处理 iframe_{fidx} 失败：', e)
                finally:
                    driver.switch_to.default_content()
        except Exception as e:
            print('查找 iframe 时出错：', e)

        # 5. 保存 Canvas 图片
        if not canvas_dataurls:
            print('❌ 未找到任何 canvas 元素或无法提取 dataURL。')
        else:
            print(f'✅ 找到 {len(canvas_dataurls)} 个 Canvas，正在保存...')
            for i, data_url in enumerate(canvas_dataurls, start=1):
                try:
                    if ',' in data_url:
                        b64 = data_url.split(',', 1)[1]
                    else:
                        b64 = data_url
                    image_data = base64.b64decode(b64)
                    img = Image.open(io.BytesIO(image_data))
                    canvas_path = os.path.join(config['output'], f'canvas_{i}.png')
                    img.save(canvas_path)
                    print(f'✅ 保存 canvas [{i}/{len(canvas_dataurls)}]')
                except Exception as e:
                    print(f'处理 canvas {i} 失败：', e)

        # 6. 下载普通图片
        if not config['only_canvas']:
            try:
                imgs = driver.find_elements(By.TAG_NAME, 'img')
                print(f'✅ 找到 {len(imgs)} 个图片标签，正在下载...')
                for i, img_el in enumerate(imgs, start=1):
                    src = img_el.get_attribute('src')
                    if not src:
                        continue
                    try:
                        with urllib.request.urlopen(src, timeout=10) as resp:
                            content = resp.read()
                            try:
                                ctype = resp.info().get_content_type()
                            except Exception:
                                ctype = None
                            ext = None
                            if ctype:
                                ext = mimetypes.guess_extension(ctype)
                            if not ext:
                                path = urllib.parse.urlparse(src).path
                                ext = os.path.splitext(path)[1]
                            if not ext:
                                ext = '.jpg'
                            img_path = os.path.join(config['output'], f'image_{i}{ext}')
                            with open(img_path, 'wb') as fh:
                                fh.write(content)
                            print(f'✅ 下载图片 [{i}/{len(imgs)}]')
                    except Exception as e:
                        print(f'❌ 下载图片失败 [{src}]:', e)
            except Exception as e:
                print('❌ 查找图片元素时出错：', e)

    except Exception as e:
        print('❌ 发生异常：', e)
    finally:
        driver.quit()
        print("\n" + "="*50)
        print("爬虫运行结束。")
        print("="*50)

if __name__ == '__main__':
    main()