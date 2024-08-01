import os
import json
import yaml
import requests

from OutPut import OutPut

Message = dict[str, str]
'''
{
    role: 'system', # or 'user', 'assistant'
    content: 'Hello, world!',
}
'''

class ChatManager:
    def __init__(self):
        self.history: dict[str, list[Message]] = {}
        
        cur_path = os.path.dirname(__file__)
        self.init_msgs: list[Message] = yaml.load(open(cur_path + '/../Config/init_msgs.yaml', encoding='UTF-8'), yaml.Loader)
        config = yaml.load(open(cur_path + '/../Config/config.yaml', encoding='UTF-8'), yaml.Loader)
        config = config['Api_Server']['chat']
        self.platform = config['platform']
        assert self.platform in ['ollama', 'zhipuai']
        self.api = config['api']
        self.key = config['key']
        self.model = config['model']
        
    def get_history(self, user: str) -> list[Message]:
        if user not in self.history:
            self.history[user] = self.init_msgs[:]
        return self.history[user]
    
    def chat(self, user: str, msg: str, role: str = 'user') -> str:
        history = self.append(user, msg, role)
        OutPut.outPut(f'[_]: 正在进行对话 {history}')
        response = self.generate(history)
        history.append(response)
        return response['content']
    
    def append(self, user: str, msg: str, role: str = 'system'):
        history = self.get_history(user)
        history.append({'role': role, 'content': msg})
        return history
    
    def _generate_ollama(self, history: list[Message]) -> Message:
        data = {
            'model': self.model,
            'messages': history,
            'stream': False
        }
        response = requests.post(self.api, data=json.dumps(data), headers={'Authorization': self.key})
        response.raise_for_status()
        return response.json()['message']
    
    def _generate_zhipuai(self, history: list[Message]) -> Message:
        data = {
            'model': self.model,
            'messages': history,
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': self.key
        }
        response = requests.post(self.api, json=data, headers=headers)
        response.raise_for_status()
        # print(f'[_]: {response.json()}')
        return response.json()['choices'][0]['message']
    
    def generate(self, history: list[Message]) -> Message:
        if self.platform == 'ollama':
            return self._generate_ollama(history)
        elif self.platform == 'zhipuai':
            return self._generate_zhipuai(history)
        else:
            raise NotImplementedError(f'Platform {self.platform} is not supported.')
    
    def clear(self, user: str):
        self.history[user] = self.init_msgs[:]