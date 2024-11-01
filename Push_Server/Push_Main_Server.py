from Api_Server.Api_Main_Server import Api_Main_Server
from Cache.Cache_Main_Server import Cache_Main_Server
from Db_Server.Db_Point_Server import Db_Point_Server
from Db_Server.Db_Main_Server import Db_Main_Server
from Api_Server.chat import ChatManager
from typing import Callable
from OutPut import OutPut
import datetime
import schedule
import yaml
import time
import os


class Push_Main_Server:
    def __init__(self, wcf, chat_mgr: ChatManager, **funcs):
        self.wcf = wcf
        current_path = os.path.dirname(__file__)
        config = yaml.load(open(current_path + '/../Config/config.yaml', encoding='UTF-8'), yaml.Loader)
        self.db_file = current_path + '/../Config/Point_db.db'
        self.Ams = Api_Main_Server(wcf=self.wcf)
        self.Dms = Db_Main_Server(wcf=self.wcf)
        self.Cms = Cache_Main_Server(wcf=self.wcf)
        self.Dps = Db_Point_Server()
        self.chat_mgr = chat_mgr

        # 下班消息
        self.Off_Work_msg = config['Push_Config']['Key_Word']['Off_Work_Msg']

        # 推送时间
        self.Morning_Push_Time = config['Push_Config']['Morning_Push_Time']
        self.Morning_Page_Tome = config['Push_Config']['Morning_Page_Time']
        self.Evening_Page_Time = config['Push_Config']['Evening_Page_Time']
        self.Off_Work_Time = config['Push_Config']['Off_Work_Time']
        self.Fish_Time = config['Push_Config']['Fish_Time']
        self.Kfc_Time = config['Push_Config']['Kfc_Time']
        
        self.master = config['Administrators'][0]

        self.funcs = funcs

    # 早安寄语推送
    def push_morning_msg(self):
        OutPut.outPut('[*]: 定时早安寄语推送中... ...')
        msg = self.Ams.get_morning()
        room_dicts = self.Dms.show_push_rooms()
        for room_id in room_dicts.keys():
            self.wcf.send_text(msg=msg, receiver=room_id)
        OutPut.outPut('[+]: 定时早安寄语推送成功！！！')

    # 早报推送
    def push_morning_page(self):
        OutPut.outPut('[*]: 定时早报推送中... ...')
        morning_msg = self.Ams.get_freebuf_news()
        room_dicts = self.Dms.show_push_rooms()
        for room_id in room_dicts.keys():
            self.wcf.send_text(msg=morning_msg, receiver=room_id)
        OutPut.outPut('[+]: 定时早报推送成功！！！')

    # 晚报推送
    def push_evening_page(self):
        OutPut.outPut('[*]: 定时晚报推送中... ...')
        evening_msg = self.Ams.get_safety_news()
        room_dicts = self.Dms.show_push_rooms()
        for room_id in room_dicts.keys():
            self.wcf.send_text(msg=evening_msg, receiver=room_id)
        OutPut.outPut('[+]: 定时晚报推送成功！！！')

    # 下班推送
    def push_off_work(self):
        OutPut.outPut('[*]: 定时下班消息推送中... ...')
        off_Work_msg = self.Off_Work_msg.replace('\\n', '\n')
        room_dicts = self.Dms.show_push_rooms()
        for room_id in room_dicts.keys():
            self.wcf.send_text(msg=off_Work_msg, receiver=room_id)
        OutPut.outPut('[+]: 定时下班消息推送成功！！！')

    # 摸鱼日记推送
    def push_fish(self):
        OutPut.outPut(f'[*]: 定时摸鱼日记推送中... ...')
        room_dicts = self.Dms.show_push_rooms()
        fish_img = self.Ams.get_fish()
        for room_id in room_dicts.keys():
            self.wcf.send_image(path=fish_img, receiver=room_id)
        OutPut.outPut('[+]: 定时摸鱼日记推送成功！！！')

    # 签到表清空
    def clear_sign(self):
        OutPut.outPut(f'[*]: 定时签到表清空中... ...')
        self.Dps.clear_sign()
        OutPut.outPut(f'[+]: 定时签到表清空成功！！！')

    # 缓存文件夹清空
    def clear_cache(self):
        OutPut.outPut(f'[*]: 定时缓存文件夹清空中... ...')
        self.Cms.delete_file()
        OutPut.outPut(f'[+]: 定时缓存文件夹清空成功！！！')

    # 每周四KFC文案推送
    def push_kfc(self):
        OutPut.outPut(f'[*]: 定时KFC文案推送中... ...')
        kfc_msg = self.Ams.get_kfc()
        room_dicts = self.Dms.show_push_rooms()
        for room_id in room_dicts.keys():
            self.wcf.send_text(msg=kfc_msg, receiver=room_id)
        OutPut.outPut(f'[+]: 定时KFC文案发送成功！！！')
    
    # 整点报时
    def push_ever_hour(self):
        now = datetime.datetime.now()
        now = now.replace(minute=0, second=0, microsecond=0)
        hour = now.hour
        time_text = now.strftime("%Y-%m-%d %H:%M:%S")
        OutPut.outPut(f'[*]: 整点报时 {time_text}')
        try:
            msg = f'[timer] now time: {time_text}'
            res = self.chat_mgr.chat(self.master, msg, role='tool')
            if res == '/skip':
                OutPut.outPut(f'[*]: 模型跳过了本次回复')
                return
            OutPut.outPut(f'[+]: Chat response: {res}')
            self.wcf.send_text(res, self.master)
        except Exception as e:
            OutPut.outPut(f'[-]: 出现错误, 错误信息: {e}')
    
    # Timeslice summary
    def push_timeslice_summary(self):
        OutPut.outPut(f'[*]: 定时时间片日结推送中... ...')
        try:
            run_tsa = self.funcs['run_tsa']
            summary = run_tsa()
            self.wcf.send_image(summary, self.master)
            OutPut.outPut(f'[+]: 定时时间片日结推送成功！！！')
        except Exception as e:
            OutPut.outPut(f'[-]: 出现错误, 错误信息: {e}')
    
    def run(self, is_running: Callable[[], bool]):
        # schedule.every().day.at(self.Morning_Push_Time).do(self.push_morning_msg)
        # schedule.every().day.at(self.Morning_Page_Tome).do(self.push_morning_page)
        # schedule.every().day.at(self.Fish_Time).do(self.push_fish)
        # schedule.every().thursday.at(self.Kfc_Time).do(self.push_kfc)
        # schedule.every().day.at(self.Evening_Page_Time).do(self.push_evening_page)
        # schedule.every().day.at(self.Off_Work_Time).do(self.push_off_work)
        schedule.every().day.at('00:00').do(self.clear_sign)
        schedule.every().day.at('03:00').do(self.clear_cache)
        # 整点报时
        schedule.every().hour.at(':00').do(self.push_ever_hour)
        # Timeslice
        schedule.every().day.at('00:15').do(self.push_timeslice_summary)
        
        OutPut.outPut(f'[+]: 已开启定时推送服务！！！')
        while is_running():
            schedule.run_pending()
            time.sleep(1)
        OutPut.outPut(f'[+]: 定时推送服务已退出！！！')


if __name__ == '__main__':
    Pms = Push_Main_Server('1')
    print(Pms.Off_Work_msg.replace('\\n', '\n'))
