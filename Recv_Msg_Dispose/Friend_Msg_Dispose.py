from Api_Server.Api_Main_Server import Api_Main_Server
from Db_Server.Db_Main_Server import Db_Main_Server
from Api_Server.chat import ChatManager
import xml.etree.ElementTree as ET
from wcferry.wxmsg import WxMsg
from datetime import datetime
from threading import Thread
from OutPut import OutPut
from wcferry import Wcf
import yaml
import os


class Friend_Msg_Dispose:
    def __init__(self, wcf: Wcf, chat_mgr: ChatManager, **funcs):
        self.wcf = wcf
        # 读取配置文件
        current_path = os.path.dirname(__file__)
        config = yaml.load(open(current_path + '/../config/config.yaml', encoding='UTF-8'), yaml.Loader)
        self.Room_Key_Word = config['Room_Key_Word']
        self.Administrators = config['Administrators']
        self.Ai_Lock = config['System_Config']['Ai_Lock']
        self.Custom_Key_Words = config['Custom_KeyWord']

        # 实例化数据库服务类
        self.Dms = Db_Main_Server(wcf=self.wcf)
        # 实例化Api类
        self.Ams = Api_Main_Server(wcf=self.wcf)

        self.chat_mgr = chat_mgr

        self.funcs = funcs

    # 消息处理
    def Msg_Dispose(self, msg):
        # 处理好友红包, 关键词进群, 好友Ai功能
        # 关键词进群
        rooms_id = self.Room_Key_Word.get(msg.content.strip())
        if rooms_id:
            OutPut.outPut(f'[*]: 检测到关键词进群, 正在处理... ...')
            Thread(target=self.Join_Room, name="关键词进群", args=(rooms_id, msg,)).start()
        elif msg.from_self():
            OutPut.outPut(f'[~]: 跳过自己发的消息')
            return
        # 处理好友红包, 转发消息给主人
        elif msg.type == 10000 and '收到红包，请在手机上查看' in msg.content.strip():
            OutPut.outPut(f'[*]: 检测到好友红包, 正在处理... ...')
            Thread(target=self.Forward_Msg, name="转发红包消息", args=(msg,)).start()
        # 转发公众号消息到推送群聊
        elif msg.type == 49 and msg.sender in self.Administrators and '转账' not in msg.content and 'gh_' in msg.content:
            OutPut.outPut(f'[*]: 检测到公众号消息, 正在处理... ...')
            return # 禁用功能
            Thread(target=self.ForWard_Gh, name="转发公众号消息", args=(msg,)).start()
        # 自动接收转账
        elif msg.type == 49 and '转账' in msg.content:
            OutPut.outPut(f'[*]: 检测到好友转账消息, 正在处理... ...')
            return # 禁用功能
            Thread(target=self.Accept_Money, name="转账消息处理", args=(msg,)).start()
        # Ai对话forward_msg
        elif msg.type == 1:
            OutPut.outPut(f'[*]: 检测到好友消息, 正在处理... ...')
            Thread(target=self.do_chat, name="Ai对话", args=(msg,)).start()
        else:
            OutPut.outPut(f'[-]: 未知类型消息 {msg}')
        # 消息转发给主人
        # OutPut.outPut(f'[*]: 检测到消息, 正在转发... ...')
        # Thread(target=self.forward_msg, name='转发消息给主人', args=(msg, )).start()

    def forward_msg(self, msg):
        if msg.type == 1:
            for administrator in self.Administrators:
                OutPut.outPut(f'[+]: 转发消息给主人: {administrator}')
                self.wcf.forward_msg(id=msg.id, receiver=administrator)

    def do_chat(self, msg: WxMsg):
        if self.Ai_Lock or msg.sender in self.Administrators:
            try:
                if msg.content == '/clear':
                    self.chat_mgr.clear(msg.sender)
                    self.wcf.send_text('[SYS] Chat history cleared.', msg.sender)
                    return
                if msg.content == '/summary':
                    if msg.sender not in self.Administrators:
                        self.wcf.send_text('[SYS] Permission denied.', msg.sender)
                        return
                    run_tsa = self.funcs.get('run_tsa')
                    if run_tsa is None:
                        self.wcf.send_text('[SYS] Summery not implemented', msg.sender)
                        return
                    summary = run_tsa()
                    self.wcf.send_image(summary, msg.sender)
                    return
                
                time_text = f'[timer] now time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
                self.chat_mgr.append(msg.sender, time_text, role='tool')
                res = self.chat_mgr.chat(msg.sender, msg.content)
                if res == '/skip':
                    OutPut.outPut(f'[*]: 模型跳过了本次回复')
                    return
                OutPut.outPut(f'[+]: Chat response: {res}')
                self.wcf.send_text(res, msg.sender)
            except Exception as e:
                self.wcf.send_text(f'[SYS] Error: {e}', msg.sender)
                OutPut.outPut(f'[-]: 出现错误, 错误信息: {e}')

    # Ai对话实现
    def get_ai(self, msg):
        if self.Ai_Lock or msg.sender in self.Administrators:
            ai_msg = self.Ams.get_ai(question=msg.content.strip())
            print(ai_msg)
            self.wcf.send_text(msg=ai_msg, receiver=msg.sender)

    # 自定义回复
    def custom_get(self, msg):
        for key, values in self.Custom_Key_Words.items():
            for value in values:
                if value == msg.content.strip():
                    OutPut.outPut(f'[+]: 调用自定义回复成功！！！')
                    self.wcf.send_text(
                        msg=f'{key}',
                        receiver=msg.sender)
                    return

    # 好友转账处理
    def Accept_Money(self, msg):
        # 只处理好友转账
        root_xml = ET.fromstring(msg.content.strip())
        title_element = root_xml.find(".//title")
        title = title_element.text if title_element is not None else None
        if '微信转账' == title and msg.sender != self.wcf.self_wxid:
            transcationid = root_xml.find('.//transcationid').text
            transferid = root_xml.find('.//transferid').text
            ret = self.wcf.receive_transfer(wxid=msg.sender, transactionid=transcationid,
                                            transferid=transferid)
            if ret:
                OutPut.outPut(
                    f'[+]: 接收转账成功, 发送人: {self.wcf.get_info_by_wxid(wxid=msg.sender).get("name")}')
            else:
                OutPut.outPut(f'[-]: 接收转账失败！！！')

    # 转发公众号文章到推送群聊 超级管理员可用
    def ForWard_Gh(self, msg):
        OutPut.outPut(f'[*]: 正在调用公众号转发接口... ...')
        push_dicts = self.Dms.show_push_rooms()
        if msg.sender in self.Administrators:
            for room_id in push_dicts.keys():
                self.wcf.forward_msg(id=msg.id, receiver=room_id)

    # 自动拉人进群
    def Join_Room(self, rooms_id, msg):
        for room_id in rooms_id:
            room_members = self.wcf.get_chatroom_members(roomid=room_id)
            if len(room_members) == 500:
                continue
            if msg.sender in room_members.keys():
                join_msg = '你小子已经进群了, 还想干嘛[旺柴]'
                self.wcf.send_text(msg=join_msg, receiver=msg.sender)
                break
            ret = self.wcf.invite_chatroom_members(wxids=msg.sender, roomid=room_id)
            if ret:
                OutPut.outPut(
                    f'[+]: 已将 [{self.wcf.get_info_by_wxid(msg.sender).get("name")}] 拉入群聊 【{self.Dms.query_room_name(room_id)}】')
                break
            else:
                OutPut.outPut(f'[-]: 拉入群聊失败, 具体请查看日志！！！')

    # 收到红包转发消息给主人
    def Forward_Msg(self, msg):
        for administrator in self.Administrators:
            msg = f'【注意】: 接收到好友 [{self.wcf.get_info_by_wxid(msg.sender).get("name")}] 的红包, 请手动领取！！！'
            ret = self.wcf.send_text(msg, receiver=administrator)
            if ret:
                OutPut.outPut(f'[+]: 接收到好友红包, 已自动转发给主人！！！')
            else:
                OutPut.outPut(f'[~]: 红包消息转发小问题, 问题不大 ~~~')
