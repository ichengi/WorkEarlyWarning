# -*-coding:utf-8-*-
# 获取接口信息，并发送失败邮件
import datetime
import smtplib
import ssl
import sys
from email.message import EmailMessage

# 发送邮件
import requests


def send_email(EMAIL_ADDRESS:str,EMAIL_PASSWORD:str,errmsg:str)->int:
    context = ssl.create_default_context()
    sender = EMAIL_ADDRESS  # 发件邮箱
    receiver = EMAIL_ADDRESS
    subject = "接口出问题啦!"
    body = errmsg
    msg = EmailMessage()
    msg['subject'] = subject  # 邮件主题
    msg['From'] = sender
    msg['To'] = receiver
    msg.set_content(body)  # 邮件内容

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465, context=context) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        return 1
    except:
        return 0

# 获取接口的数据
def get_json(url:str)->dict:
    r = requests.get(url).json()
    return r

# 判断接口是否正常
def judge_api(api_url:list)->str:
    errmsg = None
    #region 天气接口,三个定时任务
    # 天气和aqi
    if "QueryAqi"  in api_url or "QueryWeatherdata" in api_url:
        api_data = get_json(api_url)  #获取数据
        time_get_str = api_data["data"].get("gettime") # 获取时间
        time_get = datetime.datetime.strptime(time_get_str,"%Y-%m-%d %H:%M:%S") # 转换格式
        now_time = datetime.datetime.now()
        if (now_time-datetime.timedelta(hours=1)) <= time_get <= (now_time+datetime.timedelta(hours=1)): # 判断是在一小时内获取的
            pass
        else:
            errmsg = f"接口:{api_url}获取时间超时,最近一次获取是在{time_get},当前时间为{now_time},比较时间为{now_time-datetime.timedelta(hours=1)},{now_time+datetime.timedelta(hours=1)}"
    # 日数据
    if "QueryWeatherpre" in api_url:
        now_time = datetime.datetime.now()
        api_data = get_json(api_url+f"&Day={str(now_time)[:10]}")  #获取数据
        if api_data["data"] != "":
            time_get_str = api_data["data"][0].get("update_time")  # 获取时间
            time_get = datetime.datetime.strptime(time_get_str, "%Y-%m-%d %H:%M:%S")  # 转换格式
            if (now_time + datetime.timedelta(days=-2)) <= time_get <= (
                    now_time + datetime.timedelta(days=1)):  # 判断是在两天内获取的
                pass
            else:
                errmsg = f"接口:{api_url}获取时间超时,最近一次获取是在{time_get}"
        else:
            errmsg = f"接口:{api_url}获取失败"
    #endregion
    return  errmsg

if __name__ == '__main__':
    EMAIL_ADDRESS = sys.argv[1]
    EMAIL_PASSWORD = sys.argv[2]
    api_url_list = sys.argv[3:]
    errmsg = ""
    for api_url_item in api_url_list:
        single_err_msg = judge_api(api_url_item)
        if single_err_msg is not None:
            errmsg += f"|{single_err_msg}"
    if errmsg != "":
        send_email(EMAIL_ADDRESS,EMAIL_PASSWORD,errmsg)
