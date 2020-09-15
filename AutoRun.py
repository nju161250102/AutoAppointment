import json
import logging
import requests
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from selenium import webdriver


# [必填]统一身份认证登录密码
password = ""
# [必填]预约时间段开始时间 %H:%M
start_time = ""
# [必填]预约时间段结束时间 %H:%M
end_time = ""
save_data = {
    # [必填]学号
    "USER_ID": "",
    # [必填]姓名
    "USER_NAME": "",
    "DEPT_CODE": "4270",
    "DEPT_NAME": "软件学院",
    "PHONE_NUMBER": None,
    "PALCE_ID": "f881e8c2aa6f4190bc3efa13408143af",
    "BEGINNING_DATE": "",
    "ENDING_DATE": "",
    "SCHOOL_DISTRICT_CODE": "02",
    "SCHOOL_DISTRICT": "鼓楼校区",
    "LOCATION": "鼓楼男浴室",
    "PLACE_NAME": "鼓楼男浴室",
    "IS_CANCELLED": 0
}
sched = BlockingScheduler()


# 初始化Chrome
def init_chrome():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('blink-settings=imagesEnabled=false')
    client = webdriver.Chrome(chrome_options=chrome_options)
    return client


# 模拟登录获取cookies
def login(client):
    client.get("http://authserver.nju.edu.cn/authserver/login?service=http%3A%2F%2Fehallapp.nju.edu.cn%2Fqljfwapp%2Fsys%2FlwAppointmentBathroom%2F*default%2Findex.do#")
    username_elemnet = client.find_element_by_id("username")
    password_element = client.find_element_by_id("password")
    username_elemnet.send_keys(save_data["USER_ID"])
    password_element.send_keys(password)
    client.find_element_by_xpath('//*[@id="casLoginForm"]/p[4]/button').click()
    if "continue" in client.page_source:
        client.find_element_by_xpath('/html/body/div[2]/div[2]/div/div/div[2]/input[1]').click()
    return client.get_cookies()


# 预约
def ask_for_bath(session):
    result = session.post("http://ehallapp.nju.edu.cn/qljfwapp/sys/lwAppointmentBathroom/api/appointmentValidate.do", data={
        "begin_time": save_data["BEGINNING_DATE"], 
        "end_time": save_data["ENDING_DATE"],
        "palce_id": save_data["PALCE_ID"]}
    )
    result_data = json.loads(result.text)
    if result_data["code"] == 0:
        result = session.post("http://ehallapp.nju.edu.cn/qljfwapp/sys/lwAppointmentBathroom/api/appointmentSave.do?", params={"formData": json.dumps(save_data)})
        result_data = json.loads(result.text)
        if result_data["code"] == 0:
            logging.info("预约成功")
    elif result_data["code"] == 1:
        logging.warning(result_data["msg"])
    else:
        logging.error(result.text)


def everyday_job():
    # 获取cookies
    client = init_chrome()
    selenium_cookies = login(client)
    s = requests.Session()
    for d in selenium_cookies:
        c = requests.cookies.RequestsCookieJar()
        c.set(d["name"], d["value"], path=d["path"], domain=d["domain"])
        s.cookies.update(c)
    # 获取当前日期
    current_date = time.strftime("%Y-%m-%d", time.localtime())
    # 更新请求参数
    save_data["BEGINNING_DATE"] = current_date + " " + start_time
    save_data["ENDING_DATE"] = current_date + " " + end_time
    # 加入每5秒请求一次的任务，持续1分钟
    sched.add_job(ask_for_bath, 'interval', seconds=5, start_date=current_date + " 07:02:00", end_date=current_date + " 07:03:00", args=[s])
    logging.info("等待预约")
    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # 每天7：01执行一次登录操作
    sched.add_job(everyday_job, 'cron', hour=7, minute=1)
    logging.info("脚本开始执行")
    sched.start()
