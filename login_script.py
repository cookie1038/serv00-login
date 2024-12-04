import json
import asyncio
from pyppeteer import launch
from datetime import datetime, timedelta
import aiofiles
import random
import requests
import os


def format_to_iso(date):
    return date.strftime('%Y-%m-%d %H:%M:%S')


async def delay_time(ms):
    await asyncio.sleep(ms / 1000)


# 全局浏览器实例
browser = None

# 企业微信消息
message = ""


async def login(username, password, panel):
    global browser

    page = None  # 确保 page 在任何情况下都被定义
    serviceName = 'ct8' if 'ct8' in panel else 'serv00'
    try:
        if not browser:
            browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])

        page = await browser.newPage()
        url = f'https://{panel}/login/?next=/'
        await page.goto(url)

        username_input = await page.querySelector('#id_username')
        if username_input:
            await page.evaluate('''(input) => input.value = ""''', username_input)

        await page.type('#id_username', username)
        await page.type('#id_password', password)

        login_button = await page.querySelector('#submit')
        if login_button:
            await login_button.click()
        else:
            raise Exception('无法找到登录按钮')

        await page.waitForNavigation()

        is_logged_in = await page.evaluate('''() => {
            const logoutButton = document.querySelector('a[href="/logout/"]');
            return logoutButton !== null;
        }''')

        return is_logged_in

    except Exception as e:
        print(f'{serviceName}账号 {username} 登录时出现错误: {e}')
        return False

    finally:
        if page:
            await page.close()


# 显式的浏览器关闭函数
async def shutdown_browser():
    global browser
    if browser:
        await browser.close()
        browser = None


async def main():
    global message

    try:
        async with aiofiles.open('accounts.json', mode='r', encoding='utf-8') as f:
            accounts_json = await f.read()
        accounts = json.loads(accounts_json)
    except Exception as e:
        print(f'读取 accounts.json 文件时出错: {e}')
        return

    for account in accounts:
        username = account['username']
        password = account['password']
        panel = account['panel']

        serviceName = 'ct8' if 'ct8' in panel else 'serv00'
        is_logged_in = await login(username, password, panel)

        now_beijing = format_to_iso(datetime.utcnow() + timedelta(hours=8))
        if is_logged_in:
            message += f"✅*{serviceName}*账号 *{username}* 于北京时间 {now_beijing}登录面板成功！\n\n"
            print(f"{serviceName}账号 {username} 于北京时间 {now_beijing}登录面板成功！")
        else:
            message += f"❌*{serviceName}*账号 *{username}* 于北京时间 {now_beijing}登录失败\n\n❗请检查*{username}*账号和密码是否正确。\n\n"
            print(f"{serviceName}账号 {username} 登录失败，请检查{serviceName}账号和密码是否正确。")

        delay = random.randint(1000, 8000)
        await delay_time(delay)

    message += f"🔚脚本结束，如有异常点击下方按钮👇"
    await send_telegram_message(message)
    print(f'所有{serviceName}账号登录完成！')
    # 退出时关闭浏览器
    await shutdown_browser()


async def send_telegram_message(message):
    # 使用 Markdown 格式
    formatted_message = f"""
*🎯 serv00&ct8自动化保号脚本运行报告*

🕰 *北京时间*: {format_to_iso(datetime.utcnow() + timedelta(hours=8))}

⏰ *UTC时间*: {format_to_iso(datetime.utcnow())}

📝 *任务报告*:

{message}

    """
    # 获取个人信息
    try:
        async with aiofiles.open('info.json', mode='r', encoding='utf-8') as f:
            info_json = await f.read()
        info = json.loads(info_json)
    except Exception as e:
        print(f'读取 info.json 文件时出错: {e}')
        return

    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={}'.format(info['ACCESS_TOKEN'])
    data = {
        "touser": info['USER'],
        "msgtype": "text",
        "agentid": 1000004,
        "text": {
            "content": formatted_message
        },
        "safe": 0,
        "enable_id_trans": 0,
        "enable_duplicate_check": 0,
        "duplicate_check_interval": 1800
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"发送消息到企业微信失败: {response.text}")
    except Exception as e:
        print(f"发送消息到企业微信时出错: {e}")


if __name__ == '__main__':
    asyncio.run(main())
