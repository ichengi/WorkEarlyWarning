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

#获取token
def get_token(ver_url:str,payload)->str:
    response = requests.request("POST", ver_url,  data=payload)
    return response.json()['data']['access']


# 获取接口的数据
def get_json(url:str)->dict:
    r = requests.get(url).json()
    return r

# 判断接口是否正常
def judge_api(api_url:str)->str:
    global hydraulic_dict
    errmsg = None
    #region 天气接口,三个定时任务
    # 天气和aqi
    if "QueryAqi"  in api_url or "QueryWeatherdata" in api_url:
        api_data = get_json(api_url)  #获取数据
        time_get_str = api_data["data"].get("gettime") # 获取时间
        time_get = datetime.datetime.strptime(time_get_str,"%Y-%m-%d %H:%M:%S")+datetime.timedelta(hours=0) # 转换格式
        now_time = datetime.datetime.now()
        seconds = (now_time-time_get).seconds
        if seconds>60*60*1.5:# 判断是在规定时间内获取的
            errmsg = f"接口:{api_url}获取时间超时,最近一次获取是在{time_get},当前时间为{now_time},过期{float(seconds/60/60)}小时"
    # 日数据
    elif "QueryWeatherpre" in api_url:
        now_time = datetime.datetime.now()
        api_data = get_json(api_url+f"&Day={str(now_time)[:10]}")  #获取数据
        if api_data["data"] != "":
            time_get_str = api_data["data"][0].get("update_time")  # 获取时间
            time_get = datetime.datetime.strptime(time_get_str, "%Y-%m-%d %H:%M:%S")  # 转换格式
            seconds = (now_time-time_get).seconds
            if seconds > 60 * 60 * 24 * 2:  # 判断是在规定时间内获取的
                errmsg = f"接口:{api_url}获取时间超时,最近一次获取是在{time_get},过期{float(seconds/60/60)}小时"
        else:
            errmsg = f"接口:{api_url}获取失败"
    #endregion
    # region 数据中台,定时发送短信
    elif "authorization" in api_url:
        token = get_token(AUTHORIZATION_DATA_URL, AUTHORIZATION_DATA)
        headers = {"Authorization": f"JWT {token}"}
        api_data = requests.get(api_url,headers=headers).json()  # 获取数据
        #这里需要授权加token
        status = api_data['data']['data'][0]['status']
        if status == "Executed":
            pass
        else:
            errmsg = f"今日份定时发送短信失败，请尽快处理"
    #endregion
    # region 水文数据
    elif "hydraulic" in api_url:
        token= get_token(HYDRAULIC_DATA_URL,HYDRAULIC_DATA)
        headers = {"Authorization":f"JWT {token}"}
        real_time_url = hydraulic_dict.get("realtime")
        hour_url = hydraulic_dict.get("hourdata")
        day_url = hydraulic_dict.get("daydata")
        if  hour_url is not None and real_time_url is not None and day_url is not None  :
            real_time_data = requests.get(real_time_url,headers=headers).json()['data'] # 获取站点数据
            for real_time_item in real_time_data:
                stcd = real_time_item['stcd']
                state = real_time_item['state']
                if state:# 正常使用
                    #判断小时接口
                    get_time_str= get_json(f"{hour_url}{stcd}")['data'][0]['date']
                    hour_time =  datetime.datetime.strptime(get_time_str, "%Y-%m-%d %H")
                    now_time = datetime.datetime.now()
                    seconds = (now_time - hour_time).seconds
                    if seconds > 60 * 60 *2:  # 判断是在规定时间内获取的
                        errmsg = f"接口:水利小时数据获取时间超时,最近一次获取是在{hour_time},过期{float(seconds / 60/60)}小时"

                    #判断天接口
                    get_time_str = get_json(f"{day_url}{stcd}")['data'][0]['date']
                    day_time = datetime.datetime.strptime(get_time_str, "%Y-%m-%d")
                    now_time = datetime.datetime.now()
                    seconds = (now_time - day_time).seconds
                    if seconds > 60 * 60 * 24 * 2:  # 判断是在规定时间内获取的
                        errmsg += f"接口:水利天数据获取时间超时,最近一次获取是在{day_time},过期{float(seconds / 60 / 60)}小时"

                    break
    # endregion
    return  errmsg

if __name__ == '__main__':
    hydraulic_dict = {}
    EMAIL_ADDRESS = sys.argv[1]
    EMAIL_PASSWORD = sys.argv[2]
    HYDRAULIC_DATA_URL = sys.argv[3] # 请求地址
    HYDRAULIC_DATA = sys.argv[4] # 授权秘钥
    AUTHORIZATION_DATA_URL = sys.argv[5] # 请求地址
    AUTHORIZATION_DATA = sys.argv[6] # 授权秘钥
    api_url_list = sys.argv[7:]
    errmsg = ""
    for api_url_item in api_url_list:
        if "hydraulic" in api_url_item and "realtime" in api_url_item:
            hydraulic_dict['realtime'] = api_url_item
        if "hydraulic" in api_url_item and "hourdata" in api_url_item:
            hydraulic_dict['hourdata'] = api_url_item
        if "hydraulic" in api_url_item and "daydata" in api_url_item:
            hydraulic_dict['daydata'] = api_url_item
        try:
            single_err_msg = judge_api(api_url_item)
        except Exception as e:
            single_err_msg = str(e)
        if single_err_msg is not None:
            errmsg += f"|{single_err_msg}"
    if errmsg != "":
        send_email(EMAIL_ADDRESS,EMAIL_PASSWORD,errmsg)
