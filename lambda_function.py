"""DynamoDBを使って色々やる.

GET:
{"TableName": "users"}
POST:
{
    "TableName": "users",
    "Item": {
        "user_id": {"S": "hogehoge3"},
        "enabled": {"BOOL": false}
    }
}
PUT: (ただし、キーしかないのでPOSTと同じ感じになる)
{
    "TableName": "users",
    "Key": {
        "user_id": {"S": "value"}
    }
}
DELETE:
{
    "TableName": "users",
    "Key": {
        "user_id": {"S": "value"}
    }
}
"""
import asyncio
import boto3
import datetime
import json
import logging
import os
import random
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s [%(filename)s in %(lineno)d]')
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

dynamo = boto3.client('dynamodb')

# 日本時間に調整
NOW = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
# requests のユーザーエージェントを書き換えたい
HEADER = {
    'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
}
HOTPEPPER = os.environ.get('hotpepper')

TOKEN = ''
USER_ID = ''


def help() -> None:
    """メソッド一覧."""
    methods = [a for a in dir(MethodGroup) if '_' not in a]
    bubbles = []
    for _method in methods:
        description = re.sub(' {1,}', '', getattr(MethodGroup, _method).__doc__)
        args = re.split(r'\.\n', description)
        title = args[0]
        # 末尾の改行も含まれている
        description = '\n'.join((''.join(args[1:])).split('\n')[1:])
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
                        "color": "#ffffff",
                        "align": "start",
                        "size": "md",
                        "gravity": "center"
                    }
                ],
                "backgroundColor": "#27ACB2",
                "paddingAll": "15px",
                "action": {
                    "type": "postback",
                    "label": _method,
                    "data": _method,
                    "displayText": _method
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

    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/reply'
    payload = {
        'replyToken': TOKEN,
        'messages': [
            {
                "type": "flex",
                "altText": "コマンド一覧",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
        ]
    }

    res = requests.post(url, data=json.dumps(
        payload).encode('utf-8'), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': err.message if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        },
    }


def reply_message(message: str) -> None:
    """返信."""
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/reply'
    payload = {
        'replyToken': TOKEN,
        'messages': [
            {
                'type': 'text',
                'text': message,
            }
        ]
    }
    res = requests.post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def bubble_push(messages: list) -> None:
    """カルーセル（バブル）でプッシュ通知.

    引数の形式は以下
    [
        {
            'title': 'str',
            'uri': 'str',
            'description': 'str'
        }, ...
    ]
    """
    user_list = []
    for item in dynamo.scan(**{'TableName': 'users'})['Items']:
        if item['enabled']['BOOL']:
            user_list.append(item['user_id']['S'])

    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/multicast'
    bubbles = []
    if len(user_list) > 0:
        for message in messages:
            bubbles.append({
                "type": "bubble",
                "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": message.get('title'),
                            "color": "#ffffff",
                            "align": "start",
                            "size": "md",
                            "gravity": "center"
                        }
                    ],
                    "backgroundColor": "#27ACB2",
                    "paddingAll": "5px",
                    "action": {
                        "type": "uri",
                        "label": message.get('title'),
                        "uri": message.get('uri'),
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
                                  "text": message.get('description'),
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
        payload = {
            "to": user_list,
            'messages': [
                {
                    "type": "flex",
                    "altText": "通知",
                    "contents": {
                        "type": "carousel",
                        "contents": messages
                    }
                }
            ]
        }
        res = requests.post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def push_message(message: str) -> None:
    """プッシュ通知."""
    user_list = []
    for item in dynamo.scan(**{'TableName': 'users'})['Items']:
        if item['enabled']['BOOL']:
            user_list.append(item['user_id']['S'])

    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/multicast'
    if len(user_list) > 0:
        payload = {
            "to": user_list,
            'messages': [
                {
                    'type': 'text',
                    'text': message,
                }
            ]
        }
        res = requests.post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def add_user(user_id: str) -> None:
    param = {
        "TableName": "users",
        "Item": {
            "user_id": {"S": user_id},
            "enabled": {"BOOL": False}
        }
    }
    LOGGER.info(f"[DynamoDB insert] user_id: {user_id}")
    dynamo.put_item(**param)


def update_user(user_id: str, enabled: bool) -> None:
    param = {
        "TableName": "users",
        "Item": {
            "user_id": {"S": user_id},
            "enabled": {"BOOL": enabled}
        }
    }
    # dynamo.update_item(**param)
    dynamo.put_item(**param)


def delete_user(user_id: str) -> None:
    param = {
        "TableName": "users",
        "Key": {
            "user_id": {"S": user_id}
        }
    }
    dynamo.delete_item(**param)


def toggle_teiki(enabled: bool) -> None:
    update_user(USER_ID, enabled)


class CronGroup:

    @staticmethod
    async def ait() -> None:
        """アットマークITの本日の総合ランキングを返します."""
        LOGGER.info('--START-- ait')
        url = 'https://www.atmarkit.co.jp/json/ait/rss_rankindex_all_day.json'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        ret = requests.get(url, headers=HEADER)
        json_str = ret.content.decode('sjis').replace(
            'rankingindex(', '').replace(')', '').replace('\'', '"')
        json_data = json.loads(json_str)
        message = '【 アットマークITの本日の総合ランキング10件 】\n'
        msg = []
        for item in json_data['data']:
            if item:
                msg.append(f"{item['title'].replace(' ', '')}\n{item['link']}")
            if len(msg) >= 10:
                break
        message += '\n'.join(msg)
        push_message(message)
        LOGGER.info('--END-- ait')

    @staticmethod
    async def itmediaYesterday() -> None:
        """ITmediaの昨日のニュースをお伝えします.

        無ければ無いって言います。
        """
        yesterday = NOW - datetime.timedelta(days=1)
        s_yd = f'{yesterday.year}年{yesterday.month}月{yesterday.day}日'
        url = f"https://www.itmedia.co.jp/news/subtop/archive/{yesterday.strftime('%Y%m')[2:]}.html"
        ret = requests.get(url, headers=HEADER)
        site = BeautifulSoup(ret.content.decode('sjis'), 'html.parser')
        root = site.select('div.colBoxBacknumber')[
            0].select('div.colBoxInner>div')
        message = '【 ITmediaの昨日のニュース一覧 】\n'
        msg = []
        for i, item in enumerate(root):
            if 'colBoxSubhead' in item.get('class', []) and item.text == s_yd:
                for a in root[i + 1].select('ul>li'):
                    msg.append(
                        f"{a.select('a')[0].text}\nhttps:{a.select('a')[0].get('href')}")
                break
        if len(msg) > 0:
            message += '\n'.join(msg)
        else:
            message = 'ITmediaの昨日のニュースはありませんでした。'
        push_message(message)

    @staticmethod
    async def zdJapan() -> None:
        """ZDNet Japanの昨日のニュースを取得.

        無ければ無いって言います。
        """
        yesterday = NOW - datetime.timedelta(days=1)
        s_yd = yesterday.strftime('%Y-%m-%d')
        base = 'https://japan.zdnet.com'
        url = base + '/archives/'
        ret = requests.get(url, headers=HEADER)
        site = BeautifulSoup(ret.content.decode('utf8'), 'html.parser')
        root = site.select('div.pg-mod')
        message = '【 ZDNet Japanの昨日のニュース一覧 】\n'
        msg = []
        for div in root:
            span = div.select('h2.ttl-line-center>span')
            if span and span[0].text == '最新記事一覧':
                for li in div.select('ul>li'):
                    if s_yd in li.select('p.txt-update')[0].text:
                        anchor = li.select('a')[0]
                        msg.append(
                            f"{anchor.text}\n{base + anchor.get('href')}")
                break
        if len(msg) > 0:
            message += '\n'.join(msg)
        else:
            message = 'ZDNet Japanの昨日のニュースはありませんでした。'
        push_message(message)

    @staticmethod
    async def weeklyReport() -> None:
        """JPCERT から Weekly Report を取得.

        水曜日とかじゃないと何も返ってきません。
        """
        url = 'https://www.jpcert.or.jp'
        today = NOW.strftime('%Y-%m-%d')
        ret = requests.get(url, headers=HEADER)
        jpcert = BeautifulSoup(ret.content.decode('utf-8'), 'html.parser')
        whatsdate = jpcert.select('a.fl')[0].text.replace('号', '')
        if today == whatsdate:
            message = f"【 JPCERT の Weekly Report {jpcert.select('a.fl')[0].text} 】\n"
            message += url + jpcert.select('a.fl')[0].get('href') + '\n'
            wkrp = jpcert.select('div.contents')[0].select('li')
            for i, item in enumerate(wkrp, start=1):
                message += f"{i}. {item.text}\n"
            push_message(message)

    @staticmethod
    async def noticeAlert() -> None:
        """当日発表の注意喚起もしくは脆弱性関連情報を取得.

        何もなきゃ何も言いません。
        """
        url = 'https://www.jpcert.or.jp'
        today = NOW.strftime('%Y-%m-%d')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        ret = requests.get(url, headers=HEADER)
        jpcert = BeautifulSoup(ret.content.decode('utf-8'), 'html.parser')
        items = jpcert.select('div.container')
        notice = '【 JPCERT の直近の注意喚起 】\n'
        warning = '【 JPCERT の直近の脆弱性関連情報 】\n'
        notice_list = []
        warning_list = []
        for data in items:
            if data.select('h3') and data.select('h3')[0].text == '注意喚起':
                for li in data.select('ul.list>li'):
                    published = li.select('a')[0].select(
                        'span.left_area')[0].text
                    title = li.select('a')[0].select('span.right_area')[0].text
                    if today in published:
                        link = url + li.select('a')[0].get('href')
                        notice_list.append(f"{today} {title} {link}")
                    if yesterday.strftime('%Y-%m-%d') in published:
                        link = url + li.select('a')[0].get('href')
                        notice_list.append(
                            f"{yesterday.strftime('%Y-%m-%d')} {title} {link}")
            if data.select('h3') and data.select('h3')[0].text == '脆弱性関連情報':
                for li in data.select('ul.list>li'):
                    published = li.select('a')[0].select(
                        'span.left_area')[0].text.strip()
                    dt_published = datetime.datetime.strptime(
                        published, '%Y-%m-%d %H:%M')
                    title = li.select('a')[0].select('span.right_area')[0].text
                    if yesterday <= dt_published:
                        link = li.select('a')[0].get('href')
                        warning_list.append(f"{title} {link}")
        if len(notice_list) > 0:
            notice += '\n'.join(notice_list)
            push_message(notice)
        if len(warning_list) > 0:
            warning += '\n'.join(warning_list)
            push_message(warning)

    @staticmethod
    async def techCrunchJapan() -> None:
        """Tech Crunch Japanのニュースを取得する.

        RSSフィードの情報を取得するので、ちゃんと出来るか不安"""
        res = requests.get('https://jp.techcrunch.com/feed/')
        root = ET.fromstring(res.content.decode('utf8'))
        message = "Tech Crunch Japan のRSSフィードのニュースです。\n"
        msg = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                msg.append(child[0].text + '\n' + child[1].text)
        if len(msg) == 0:
            message += '直近のニュースはありませんでした'
        else:
            message += '\n'.join(msg)
        push_message(message)

    @staticmethod
    async def techRepublicJapan() -> None:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        yesterday = datetime.datetime.strptime(yesterday.strftime('%Y%m%d'), '%Y%m%d')
        res = requests.get('https://japan.techrepublic.com/rss/latest/')
        root = ET.fromstring(res.content.decode('utf8'))
        message = "TechRepublic Japan のRSSフィードのニュースです。"
        msg = []
        for child in root:
            if len(msg) >= 12:
                break
            if 'item' in child.tag.lower():
                date_obj = datetime.datetime.strptime(child[1].text[0:10], '%Y-%m-%d')
                if yesterday <= date_obj:
                    bubble = {
                        'title': child[3].text,
                        'uri': child[4].text,
                        'description': child[4].text[0:50] + '...'
                    }
                    msg.append(bubble)
        if len(msg) == 0:
            message += '\n直近のニュースはありませんでした'
        push_message(message)
        if len(msg) > 0:
            bubble_push(msg)


class MethodGroup:
    """やりたい処理を定義."""

    @staticmethod
    def lunch(args: list) -> None:
        """ランチ営業店舗検索.

        lunchコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': HOTPEPPER,
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
            headers=HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) > 0:
            shop = random.choice(shops)
            message = f'{shop["name"]}\n{shop["urls"]["pc"]}\n'
        else:
            message = '検索結果がありません\n'
        message += '　　Powered by ホットペッパー Webサービス'
        reply_message(message)

    @staticmethod
    def qiita(args: list) -> None:
        """Qiita新着記事取得.

        qiitaコマンドでQiitaの新着記事を3件取得します。
        """
        res = requests.get('https://qiita.com/api/v2/items?page=1&per_page=3',
                           headers=HEADER)
        data = res.json()
        msg = []
        for d in data:
            msg.append(f"{d['title']}\n{d['url']}")
        message = '\n'.join(msg)
        reply_message(message)

    @staticmethod
    def nomitai(args: list) -> None:
        """居酒屋検索.

        nomitaiコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': HOTPEPPER,
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
            headers=HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) == 0:
            message = '検索結果がありません\n'
        else:
            shop = random.choice(shops)
            message = f"{shop['name']}\n{shop['urls']['pc']}\n"
        message += '　　Powered by ホットペッパー Webサービス'
        reply_message(message)

    @staticmethod
    def teiki(args: list) -> None:
        """定期実行.

        有効にしたら、毎日正午にニュース等を取得します。
        有効かどうかをチェックするには、このメソッドを実行してください。
        """
        is_enabled = False
        for item in dynamo.scan(**{"TableName": "users"})['Items']:
            if item['user_id']['S'] == USER_ID:
                is_enabled = item['enabled']['BOOL']
        if is_enabled:
            reply_message("有効になっています\n無効にするには、「定期無効」と入力してください")
        else:
            reply_message("無効になっています\n有効にするには、「定期有効」と入力してください")
        return


async def runner():
    await CronGroup.ait()
    await CronGroup.itmediaYesterday()
    await CronGroup.zdJapan()
    await CronGroup.weeklyReport()
    await CronGroup.noticeAlert()
    await CronGroup.techCrunchJapan()
    await CronGroup.techRepublicJapan()


def lambda_handler(event, context):
    '''Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    '''
    global TOKEN, USER_ID
    LOGGER.info('--LAMBDA START--')
    LOGGER.info(f"event: {json.dumps(event)}")
    LOGGER.info(f"context: {context}")
    try:
        body = json.loads(event.get('body'))
        USER_ID = body.get('events', [])[0]['source']['userId']
    except Exception:
        body = {}
    LOGGER.info(f"body: {body}")
    if isinstance(event, dict) and event.get('source') == 'aws.events':
        # CloudWatch Event のやつ
        asyncio.run(runner())
    # DynamoDBを使う時のデフォルトの使い方
    # operations = {
    #     'DELETE': lambda dynamo, x: dynamo.delete_item(**x),
    #     'GET': lambda dynamo, x: dynamo.scan(**x),
    #     'POST': lambda dynamo, x: dynamo.put_item(**x),
    #     'PUT': lambda dynamo, x: dynamo.update_item(**x),
    # }
    #
    # operation = event['httpMethod']
    # if operation in operations:
    #     payload = event['queryStringParameters'] if operation == 'GET' else json.loads(event['body'])
    #     return respond(None, operations[operation](dynamo, payload))
    # else:
    #     return respond(ValueError('Unsupported method "{}"'.format(operation)))
    # LINE follow user
    if isinstance(body, dict) and body.get('events', [{'type': ''}])[0]['type'] == 'follow':
        if body['events'][0]['source']['type'] == 'user':
            user_id = body['events'][0]['source']['userId']
            add_user(user_id)
    # LINE unfollow user
    if isinstance(body, dict) and body.get('events', [{'type': ''}])[0]['type'] == 'unfollow':
        if body['events'][0]['source']['type'] == 'user':
            user_id = body['events'][0]['source']['userId']
            delete_user(user_id)
    text = ''
    # LINE webhook
    if isinstance(body, dict):
        for event in body.get('events', []):
            TOKEN = event.get('replyToken', '')
            text = event.get('message', {}).get('text')
            # postback の場合はメソッドのデフォルトで動作するように設定
            if event.get('postback', {}).get('data'):
                text = event['postback']['data']
    text = text.replace('　', ' ')
    args = text.split(' ')
    if len(args) > 0 and args[0] == 'コマンド':
        help()
    elif len(args) > 0 and args[0] == '定期無効':
        toggle_teiki(False)
        reply_message('定期実行を無効にしました')
    elif len(args) > 0 and args[0] == '定期有効':
        toggle_teiki(True)
        reply_message('定期実行を有効にしました')
    elif (len(args) > 0 and getattr(MethodGroup, args[0], None)):
        LOGGER.info(f"method: {args[0]}, param: {args[1:]}")
        getattr(MethodGroup, args[0])(args[1:])

    payload = {
        'messages': [
            {
                'type': 'text',
                'text': '200 OK'
            },
        ],
    }

    ret = {
        'statusCode': '200',
        'body': json.dumps(payload, ensure_ascii=False),
        'headers': {
            'Content-Type': 'application/json',
        },
    }
    LOGGER.info(f'[RETURN] {ret}')
    LOGGER.info('--LAMBDA END--')
    return ret
