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
import re
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from ReplyMethodGroup import MethodGroup

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


def reply_bubble(bubbles: list) -> None:
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
    LOGGER.info(f"[REQUEST] [URL]{url} [PAYLOAD]{json.dumps(payload, ensure_ascii=False)}")
    res = requests.post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


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
                # "size": "kilo",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": message.get('title'),
                            "color": "#2f3739",
                            "align": "start",
                            "size": "md",
                            "wrap": True,
                            "gravity": "center"
                        }
                    ],
                    "backgroundColor": "#9bcfd1",
                    "paddingAll": "5px",
                    "action": {
                        "type": "uri",
                        "label": message.get('title')[0:20],
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
                            "action": {
                                "type": "uri",
                                "label": message.get('title', '')[0:20],
                                "uri": message.get('uri', ''),
                            },
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
                        "contents": bubbles
                    }
                }
            ]
        }
        LOGGER.info(f"[REQUEST] param: {json.dumps(payload)}")
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


def update_user(user_id: str, params: dict) -> None:
    """ユーザー情報更新.html

    :param str user_id: 対象のユーザーID
    :param dict params: ユーザーに対して登録するパラメータを指定する

        {
            "enabled": {"BOOL": True},
            ...
        }
    """
    param = {
        "TableName": "users",
        "Item": {
            "user_id": {"S": user_id},
        }
    }
    param['Item'].update(params)
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
    """定期実行の有効化、もしくは無効化."""
    params = {
        'enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


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
        message = "Tech Crunch Japan のRSSフィードのニュースです。"
        msg = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                bubble = {
                    'title': child[0].text,
                    'uri': child[1].text,
                    'description': '説明はありません'
                }
                for mago in child:
                    if 'encoded' in mago.tag.lower():
                        step1 = re.sub(r'^\<\!\[CDATA.*1024px" />', '', mago.text)
                        step2 = re.sub(r"<[^>]*?>", '', step1)
                        bubble['description'] = step2[0:100] + '…'
                msg.append(bubble)
        if len(msg) == 0:
            message += '\n直近のニュースはありませんでした'
        push_message(message)
        if len(msg) > 0:
            bubble_push(msg)

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
                        'description': re.sub('<.*>', '', child[5].text)
                    }
                    msg.append(bubble)
        if len(msg) == 0:
            message += '\n直近のニュースはありませんでした'
        push_message(message)
        if len(msg) > 0:
            bubble_push(msg)


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
    LOGGER.info(f"body: {json.dumps(body)}")
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
    text = text.replace('　', ' ').replace('\n', ' ')
    args = text.split(' ')
    methodGroup = MethodGroup(dynamo, USER_ID)
    if len(args) > 0 and args[0] == 'コマンド':
        reply_bubble(methodGroup._help())
    elif len(args) > 0 and args[0] == '定期無効':
        toggle_teiki(False)
        reply_message('定期実行を無効にしました')
    elif len(args) > 0 and args[0] == '定期有効':
        toggle_teiki(True)
        reply_message('定期実行を有効にしました')
    else:
        func = methodGroup._method_search(args[0])
        if func:
            LOGGER.info(f"method: {func}, param: {args[1:]}")
            message = getattr(methodGroup, func)(args[1:])
            if message:
                reply_message(message)

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
