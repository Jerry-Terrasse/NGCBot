import re
import os
import json
import yaml
import requests
import fnmatch

from visualize import visualize as draw_pie

class NapCat:
    def __init__(self, api: str, group_id: int):
        self.api = api
        self.group_id = group_id
    
    def fetch_raw(self, count: int = 30):
        url = f"{self.api}/get_group_msg_history"
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "group_id": self.group_id,
            "count": count
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        msg = response.json()
        assert msg['status'] == 'ok'
        msg = msg['data']['messages']
        raw = [m['raw_message'] for m in msg]
        return raw
    
    def parse(self, raw: list[str], stop_at) -> list[tuple[int, str, str]]:
        pattern = re.compile(r"^\d+ ")
        raw = [r for r in raw if pattern.match(r)]
        records = []
        for r in raw[::-1]:
            record = r.split(' ')
            assert len(record) == 2 or len(record) == 3
            record = (int(record[0]), record[1], record[-1])
            if records: # check continuity
                prev, cur = records[-1][0], record[0]
                assert (prev, cur) == (0, 23) or prev == cur + 1
            records.append(record)
            if record[0] == stop_at:
                break
        else:
            raise ValueError(f"Stop point {stop_at} not found")

        records = records[::-1]
        for i in range(1, len(records)):
            records[i] = (records[i-1][0]+1, *records[i][1:])
        return records
    
    def get_records(self, stop_at: int = 8, count: int = 30):
        raw = self.fetch_raw(count)
        records = self.parse(raw, stop_at)
        return records

class Analyzer:
    def __init__(self, api: str, group_id: int):
        self.napcat = NapCat(api, group_id)
        self.config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

        self.mapping: list[tuple[str, str]] = []
        self.config = {}
        self.load_mapping()
        
    def load_mapping(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.mapping = []
        for category in self.config['category']:
            name = category['name']
            for keyword in category['patterns']:
                self.mapping.append((keyword, name))
    
    def apply_mapping(self, items: list[str]) -> list[str]:
        results = []
        for item in items:
            for keyword, category in self.mapping:
                if fnmatch.fnmatch(item, keyword):
                    results.append(category)
                    break
            else:
                results.append("Unknown")
        return results
    
    def analyze(self, stop_at: int = 8, count: int = 30):
        records = self.napcat.get_records(stop_at, count)
        slices = [r[k] for r in records for k in (1, 2)]
        slices = self.apply_mapping(slices)
        cnt = {}
        for s in slices:
            cnt[s] = cnt.get(s, 0) + 1
        return records, slices, cnt
    
    def visualize(self, slices: list[str], start_at: int = 8):
        draw_pie(slices, self.config['category'], start_at)

if __name__ == "__main__":
    pass