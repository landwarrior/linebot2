"""応答メッセージをするメソッド群."""
import logging
import os
import random
import re

import requests

from decos import log

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

LOGGER = logging.getLogger(name="Lambda")


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
    @log(LOGGER)
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

    @log(LOGGER)
    def lunch(self, args: list) -> None:
        """ランチ営業店舗検索.

        スペース区切りもしくは改行区切りで二つ以上キーワードを入力すると場所での検索も可能です。
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

    @log(LOGGER)
    def qiita(self, args: list) -> None:
        """Qiita新着記事取得.

        Qiitaの新着記事を3件取得します。
        """
        res = requests.get('https://qiita.com/api/v2/items?page=1&per_page=3',
                           headers=self.HEADER)
        data = res.json()
        msg = []
        for d in data:
            msg.append(f"{d['title']}\n{d['url']}")
        message = '\n'.join(msg)
        return message

    @log(LOGGER)
    def nomitai(self, args: list) -> None:
        """居酒屋検索.

        スペース区切りもしくは改行区切りで二つ以上キーワードを入力すると場所での検索も可能です。
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

    @log(LOGGER)
    def teiki(self, args: list) -> None:
        """定期実行.

        有効にしたら、毎日正午にニュース等を取得します。
        有効かどうかをチェックするには、このメソッドを実行してください。
        """
        check = '定期実行の確認'
        for item in self.dynamo.scan(**{"TableName": "users"})['Items']:
            if item['user_id']['S'] == self.user_id:
                bool_str = '有効' if item.get(
                    'enabled', {}).get('BOOL', False) else '無効'
                check += f"\n定期実行： {bool_str}"
                bool_str = '有効' if item.get(
                    'ait_enabled', {}).get('BOOL', False) else '無効'
                check += f"\n(1)アットマークITランキング： {bool_str}"
                bool_str = '有効' if item.get(
                    'ait_new_all_enabled', {}).get('BOOL', False) else '無効'
                check += f"\n(2)アットマークITの全フォーラムの新着記事： {bool_str}"
                bool_str = '有効' if item.get(
                    'smart_jp_enabled', {}).get('BOOL', False) else '無効'
                check += f"\n(3)スマートジャパンの新着記事： {bool_str}"
                bool_str = '有効' if item.get(
                    'itmedia_news_enabled', {}).get('BOOL', False) else '無効'
                check += f"\n(4)ITmedia NEWS 最新記事一覧： {bool_str}"
                bool_str = '有効' if item.get(
                    'zdjapan_enabled', {}).get('BOOL', False) else '無効'
                check += f"\n(5)ZDNet Japan 最新情報 総合： {bool_str}"
                bool_str = '有効' if item.get(
                    'tech_republic_jp_enabled', {}).get(
                        'BOOL', False) else '無効'
                check += f"\n(6)TechRepublic Japan の最新ニュース： {bool_str}"
                bool_str = '有効' if item.get(
                    'uxmilk', {}).get('BOOL', False) else '無効'
                check += f"\n(7)UX MILK の最新ニュース： {bool_str}"
        check += '\n定期実行を有効にするには、「定期有効」と入力してください'
        check += '\n定期実行を無効にするには、「定期無効」と入力してください'
        check += '\nそれぞれの実行を切り替えるには、「番号(有効|無効)」と入力してください'
        return check

        # if is_enabled:
        #     return "有効になっています\n無効にするには、「定期無効」と入力してください"
        # return "無効になっています\n有効にするには、「定期有効」と入力してください"
