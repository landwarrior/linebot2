"""応答メッセージをするメソッド群."""
import os
import random
import re

import requests

ITEM = {
    'lunch': {
        'name': 'ランチ検索',
        'must': ['ランチ', '検索'],
    },
    'qiita': {
        'name': 'Qiitaの新着',
        'must': ['Qiita', '新着'],
    },
    'nomitai': {
        'name': '居酒屋検索',
        'must': ['居酒屋', '検索'],
    },
    'teiki': {
        'name': '定期実行確認',
        'must': ['定期', '確認'],
    },
}


class MethodGroup:
    """やりたい処理を定義."""

    def __init__(self, dynamo, user_id):
        self.dynamo = dynamo
        self.user_id = user_id
        self.HOTPEPPER = os.environ.get('hotpepper')
        self.HEADER = {
            'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
        }

    @classmethod
    def _help(cls):
        """メソッド一覧."""
        methods = [a for a in dir(cls) if '_' not in a]
        bubbles = []
        for _method in methods:
            description = re.sub(' {1,}', '', getattr(cls, _method).__doc__)
            args = re.split(r'\.\n', description)
            title = args[0]
            # 末尾の改行も含まれている
            description = '\n'.join((''.join(args[1:])).split('\n')[1:])
            label = ITEM.get(_method, {}).get('name')
            bubbles.append({
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": title,
                            "color": "#2f3739",
                            "align": "start",
                            "size": "md",
                            "gravity": "center"
                        }
                    ],
                    "backgroundColor": "#9bcfd1",
                    "paddingAll": "15px",
                    "action": {
                        "type": "postback",
                        "label": label,
                        "data": label,
                        "displayText": label
                    }
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                              {
                                  "type": "text",
                                  "text": description,
                                  "color": "#8C8C8C",
                                  "size": "sm",
                                  "wrap": True
                              }
                            ],
                            "flex": 1
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "12px",
                },
                "styles": {
                    "footer": {
                        "separator": False
                    }
                }
            })

        return bubbles

    def _method_search(self, text):
        """対象のメソッドがあればそのメソッド名を返す."""
        for key, value in ITEM.items():
            check = 0
            for must in value['must']:
                if must in text:
                    check += 1
            if check == len(value['must']):
                return key

    def lunch(self, args: list) -> None:
        """ランチ営業店舗検索.

        lunchコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': self.HOTPEPPER,
            'large_service_area': 'SS10',  # 関東
            'range': '3',
            'order': '2',
            'type': 'lite',
            'format': 'json',
            'count': '100',
            'lunch': '1',
        }
        if not args or len(args) == 1:
            _param['lat'] = os.environ['default_lat']
            _param['lng'] = os.environ['default_lng']
        if len(args) > 0:
            _param['keyword'] = ' '.join(list(args))
        hotpepper = requests.get(
            'http://webservice.recruit.co.jp/hotpepper/gourmet/v1/',
            params=_param,
            headers=self.HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) > 0:
            shop = random.choice(shops)
            message = f'{shop["name"]}\n{shop["urls"]["pc"]}\n'
        else:
            message = '検索結果がありません\n'
        message += '　　Powered by ホットペッパー Webサービス'
        return message

    def qiita(self, args: list) -> None:
        """Qiita新着記事取得.

        qiitaコマンドでQiitaの新着記事を3件取得します。
        """
        res = requests.get('https://qiita.com/api/v2/items?page=1&per_page=3',
                           headers=self.HEADER)
        data = res.json()
        msg = []
        for d in data:
            msg.append(f"{d['title']}\n{d['url']}")
        message = '\n'.join(msg)
        return message

    def nomitai(self, args: list) -> None:
        """居酒屋検索.

        nomitaiコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': self.HOTPEPPER,
            'large_service_area': 'SS10',  # 関東
            'range': '5',
            'order': '2',
            'type': 'lite',
            'format': 'json',
            'count': '100',
        }
        if not args or len(args) == 1:
            _param['lat'] = os.environ['default_lat']
            _param['lng'] = os.environ['default_lng']
            if not args:
                # デフォルトは居酒屋
                _param['genre'] = 'G001'
        if len(args) > 0:
            _param['keyword'] = ' '.join(list(args))
        if len(args) >= 2:
            # 範囲を絞る
            _param['range'] = 3

        hotpepper = requests.get(
            'http://webservice.recruit.co.jp/hotpepper/gourmet/v1/',
            params=_param,
            headers=self.HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) == 0:
            message = '検索結果がありません\n'
        else:
            shop = random.choice(shops)
            message = f"{shop['name']}\n{shop['urls']['pc']}\n"
        message += '　　Powered by ホットペッパー Webサービス'
        return message

    def teiki(self, args: list) -> None:
        """定期実行.

        有効にしたら、毎日正午にニュース等を取得します。
        有効かどうかをチェックするには、このメソッドを実行してください。
        """
        is_enabled = False
        for item in self.dynamo.scan(**{"TableName": "users"})['Items']:
            if item['user_id']['S'] == self.user_id:
                is_enabled = item['enabled']['BOOL']
        if is_enabled:
            return "有効になっています\n無効にするには、「定期無効」と入力してください"
        return "無効になっています\n有効にするには、「定期有効」と入力してください"
