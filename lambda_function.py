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
PUT: (初期に調べたときは以下のようにキーが必要だと思ったが、POSTと同じで出来たので不要かも)
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

import requests

from ReplyMethodGroup import MethodGroup
from CronGroup import CronGroup

LOGGER = logging.getLogger(name="Lambda")
LOGGER.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s [%(filename)s in %(lineno)d]')
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

dynamo = boto3.client('dynamodb')

# 日本時間に調整
NOW = datetime.datetime.now(datetime.timezone.utc) + \
                            datetime.timedelta(hours=9)
# requests のユーザーエージェントを書き換えたい
HEADER = {
    'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
}

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
    LOGGER.info(
        f"[REQUEST] [URL]{url} [PAYLOAD]{json.dumps(payload, ensure_ascii=False)}")
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
    res = requests.post(url, data=json.dumps(
        payload).encode('utf-8'), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def create_bubble_push_messages(content: dict) -> list:
    """カルーセル（バブル）でプッシュ通知.

    引数の形式は以下
    {
        'text': 'str',
        'messages': [
            {
                'title': 'str',
                'uri': 'str',
                'description': 'str'
            }, ...
        ]
    }
    """
    messages_response = []
    bubbles = []
    for message in content.get('messages'):
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
                        "color": "#2f3739",
                        "align": "start",
                        "size": "md",
                        "wrap": True,
                        "gravity": "center"
                    }
                ],
                "backgroundColor": "#9bcfd1",
                "paddingAll": "4px",
                "action": {
                    "type": "uri",
                    "label": message.get('title', '')[0:20],
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
                              "size": "xs",
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
                "spacing": "xs",
                "paddingAll": "4px",
            },
            "styles": {
                "footer": {
                    "separator": False
                }
            }
        })
        if len(bubbles) >= 12:
            messages_response.append({
                "type": "flex",
                "altText": "通知",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            })
            bubbles = []
    if len(bubbles) > 0:
        messages_response.append({
            "type": "flex",
            "altText": "通知",
            "contents": {
                "type": "carousel",
                "contents": bubbles
            }
        })
    return messages_response


def bubble_push(user_list: list, messages: list) -> None:
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
    if not user_list:
        # 送信先がなければ何もしない
        return
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/multicast'
    payload = {
        "to": user_list,
        'messages': messages
    }
    LOGGER.info(f"[REQUEST] param: {json.dumps(payload)}")
    res = requests.post(url, data=json.dumps(
        payload).encode('utf-8'), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def push_message(user_list: list, message: str) -> None:
    """プッシュ通知."""
    if not user_list:
        # 送信先がなければ何もしない
        return
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/multicast'
    payload = {
        "to": user_list,
        'messages': [
            {
                'type': 'text',
                'text': message,
            }
        ]
    }
    LOGGER.info(f"[REQUEST] param: {json.dumps(payload)}")
    res = requests.post(url, data=json.dumps(
        payload).encode('utf-8'), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


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
    """ユーザー情報更新.

    :param str user_id: 対象のユーザーID
    :param dict params: ユーザーに対して登録するパラメータを指定する

        {
            "enabled": {"BOOL": True},
            ...
        }
    """
    items = {}
    for item in dynamo.scan(**{'TableName': 'users'})['Items']:
        if user_id == item['user_id']['S']:
            items.update(item)
    param = {
        "TableName": "users",
        "Item": items
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


def toggle_ait(enabled: bool) -> None:
    """アットマークITのランキングの定期実行有効化、もしくは無効化."""
    params = {
        'ait_enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


def toggle_ait_new_all(enabled: bool) -> None:
    """アットマークITの新着の定期実行有効化、もしくは無効化."""
    params = {
        'ait_new_all_enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


def toggle_smart_jp(enabled: bool) -> None:
    """スマートジャパンの新着の定期実行有効化、もしくは無効化."""
    params = {
        'smart_jp_enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


def toggle_itmedia_news(enabled: bool) -> None:
    """ITMedia NEWSの新着の定期実行有効化、もしくは無効化."""
    params = {
        'itmedia_news_enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


def toggle_zdjapan(enabled: bool) -> None:
    """ZDNet Japanの新着の定期実行有効化、もしくは無効化."""
    params = {
        'zdjapan_enabled': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


def toggle_uxmilk(enabled: bool) -> None:
    """UX MILKの新着の定期実行有効化、もしくは無効化."""
    params = {
        'uxmilk': {'BOOL': enabled}
    }
    update_user(USER_ID, params)


async def runner():
    user_list = []
    for item in dynamo.scan(**{'TableName': 'users'})['Items']:
        if item['enabled']['BOOL']:
            user_list.append({
                'user_id': item['user_id']['S'],
                'ait_enabled': item.get('ait_enabled', {}).get('BOOL', False),
                'ait_new_all_enabled': item.get('ait_new_all_enabled', {}).get('BOOL', False),
                'smart_jp_enabled': item.get('smart_jp_enabled', {}).get('BOOL', False),
                'itmedia_news_enabled': item.get('itmedia_news_enabled', {}).get('BOOL', False),
                'zdjapan_enabled': item.get('zdjapan_enabled', {}).get('BOOL', False),
                'tech_republic_jp_enabled': item.get('tech_republic_jp_enabled', {}).get('BOOL', False),
                'uxmilk': item.get('uxmilk', {}).get('BOOL', False),
            })
    ait = await CronGroup.ait()
    ait_new_all = await CronGroup.ait_new_all()
    smart_jp = await CronGroup.smart_jp()
    itmedia_news = await CronGroup.itmedia_news()
    zdjapan = await CronGroup.zdjapan()
    weekly_report = await CronGroup.weeklyReport()
    notice = await CronGroup.jpcertNotice()
    alert = await CronGroup.jpcertAlert()
    uxmilk = await CronGroup.uxmilk()
    push_target_users = {
        'ait': [],
        'ait_new_all': [],
        'smart_jp': [],
        'itmedia_news': [],
        'zdjapan': [],
        'tech_republic_jp': [],
        'weekly_report': [],
        'notice': [],
        'uxmilk': [],
    }
    for user in user_list:
        if user['ait_enabled']:
            push_target_users['ait'].append(user['user_id'])
        if user['ait_new_all_enabled']:
            push_target_users['ait_new_all'].append(user['user_id'])
        if user['smart_jp_enabled']:
            push_target_users['smart_jp'].append(user['user_id'])
        if user['itmedia_news_enabled']:
            push_target_users['itmedia_news'].append(user['user_id'])
        if user['zdjapan_enabled']:
            push_target_users['zdjapan'].append(user['user_id'])
        if user['tech_republic_jp_enabled']:
            push_target_users['tech_republic_jp'].append(user['user_id'])
        if user['uxmilk']:
            push_target_users['uxmilk'].append(user['user_id'])
        push_target_users['weekly_report'].append(user['user_id'])
        push_target_users['notice'].append(user['user_id'])
    if ait:
        messages = create_bubble_push_messages(ait)
        push_message(push_target_users['ait'], ait['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['ait'], messages)
    if ait_new_all:
        messages = create_bubble_push_messages(ait_new_all)
        push_message(push_target_users['ait_new_all'], ait_new_all['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['ait_new_all'], messages)
    if smart_jp:
        messages = create_bubble_push_messages(smart_jp)
        push_message(push_target_users['smart_jp'], smart_jp['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['smart_jp'], messages)
    if itmedia_news:
        messages = create_bubble_push_messages(itmedia_news)
        push_message(push_target_users['itmedia_news'], itmedia_news['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['itmedia_news'], messages)
    if zdjapan:
        messages = create_bubble_push_messages(zdjapan)
        push_message(push_target_users['zdjapan'], zdjapan['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['zdjapan'], messages)
    if uxmilk:
        messages = create_bubble_push_messages(uxmilk)
        push_message(push_target_users['uxmilk'], uxmilk['text'])
        if len(messages) > 0:
            bubble_push(push_target_users['uxmilk'], messages)
    if weekly_report:
        push_message(push_target_users['weekly_report'], weekly_report['text'])
    if notice:
        push_message(push_target_users['notice'], notice['text'])
    if alert:
        push_message(push_target_users['notice'], alert['text'])


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
    elif len(args) > 0 and args[0] == '1有効':
        toggle_ait(True)
        reply_message('アットマークITランキングを有効にしました')
    elif len(args) > 0 and args[0] == '1無効':
        toggle_ait(False)
        reply_message('アットマークITランキングを無効にしました')
    elif len(args) > 0 and args[0] == '2有効':
        toggle_ait_new_all(True)
        reply_message('アットマークITの全フォーラムの新着記事を有効にしました')
    elif len(args) > 0 and args[0] == '2無効':
        toggle_ait_new_all(False)
        reply_message('アットマークITの全フォーラムの新着記事を無効にしました')
    elif len(args) > 0 and args[0] == '3有効':
        toggle_smart_jp(True)
        reply_message('スマートジャパンの新着記事を有効にしました')
    elif len(args) > 0 and args[0] == '3無効':
        toggle_smart_jp(False)
        reply_message('スマートジャパンの新着記事を無効にしました')
    elif len(args) > 0 and args[0] == '4有効':
        toggle_itmedia_news(True)
        reply_message('ITmedia NEWS 最新記事一覧を有効にしました')
    elif len(args) > 0 and args[0] == '4無効':
        toggle_itmedia_news(False)
        reply_message('ITmedia NEWS 最新記事一覧を無効にしました')
    elif len(args) > 0 and args[0] == '5有効':
        toggle_zdjapan(True)
        reply_message('ZDNet Japan 最新情報 総合を有効にしました')
    elif len(args) > 0 and args[0] == '5無効':
        toggle_zdjapan(False)
        reply_message('ZDNet Japan 最新情報 総合を無効にしました')
    elif len(args) > 0 and args[0] == '6有効':
        toggle_uxmilk(True)
        reply_message('UX MILK の最新ニュースを有効にしました')
    elif len(args) > 0 and args[0] == '6無効':
        toggle_uxmilk(False)
        reply_message('UX MILK の最新ニュースを無効にしました')
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
