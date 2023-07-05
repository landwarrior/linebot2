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
import json
import logging
import os

import boto3

import requests
from ReplyAction import ReplyAction
from CronAction import CronAction


LOGGER = logging.getLogger(name="Lambda")
LOGGER.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s [%(filename)s in %(lineno)d]"
)
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

dynamo = boto3.client("dynamodb")

TOKEN = ""
USER_ID = ""


# def respond(err, res=None):
#     return {
#         "statusCode": "400" if err else "200",
#         "body": err.message if err else json.dumps(res),
#         "headers": {
#             "Content-Type": "application/json",
#         },
#     }


def reply_message(message: str) -> None:
    """返信."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/reply"
    payload = {
        "replyToken": TOKEN,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }
    res = requests.post(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}"
    )


def reply(message: dict) -> None:
    """返信."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/reply"
    payload = {"replyToken": TOKEN, "messages": [message]}
    res = requests.post(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}"
    )


def add_user(user_id: str) -> None:
    param = {
        "TableName": "users",
        "Item": {"user_id": {"S": user_id}, "enabled": {"BOOL": False}},
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
    for item in dynamo.scan(**{"TableName": "users"})["Items"]:
        if user_id == item["user_id"]["S"]:
            items.update(item)
    param = {"TableName": "users", "Item": items}
    param["Item"].update(params)
    # dynamo.update_item(**param)
    dynamo.put_item(**param)


def delete_user(user_id: str) -> None:
    """ユーザー削除."""
    param = {"TableName": "users", "Key": {"user_id": {"S": user_id}}}
    dynamo.delete_item(**param)


def toggle_teiki(enabled: bool) -> None:
    """定期実行の有効化、もしくは無効化."""
    params = {"enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_ait(enabled: bool) -> None:
    """アットマークITのランキングの定期実行有効化、もしくは無効化."""
    params = {"ait_enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_ait_new_all(enabled: bool) -> None:
    """アットマークITの新着の定期実行有効化、もしくは無効化."""
    params = {"ait_new_all_enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_smart_jp(enabled: bool) -> None:
    """スマートジャパンの新着の定期実行有効化、もしくは無効化."""
    params = {"smart_jp_enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_itmedia_news(enabled: bool) -> None:
    """ITMedia NEWSの新着の定期実行有効化、もしくは無効化."""
    params = {"itmedia_news_enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_zdjapan(enabled: bool) -> None:
    """ZDNet Japanの新着の定期実行有効化、もしくは無効化."""
    params = {"zdjapan_enabled": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_uxmilk(enabled: bool) -> None:
    """UX MILKの新着の定期実行有効化、もしくは無効化."""
    params = {"uxmilk": {"BOOL": enabled}}
    update_user(USER_ID, params)


def toggle_techTarget(enabled: bool) -> None:
    """TechTargetの新着の定期実行有効化、もしくは無効化."""
    params = {"techTarget": {"BOOL": enabled}}
    update_user(USER_ID, params)


def lambda_handler(event, context):
    """Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    """
    global TOKEN, USER_ID
    LOGGER.info("--LAMBDA START--")
    LOGGER.info(f"event: {json.dumps(event)}")
    LOGGER.info(f"context: {context}")
    try:
        body = json.loads(event.get("body"))
        USER_ID = body.get("events", [])[0]["source"]["userId"]
    except Exception:
        body = {}
    LOGGER.info(f"body: {json.dumps(body)}")
    if isinstance(event, dict) and event.get("source") == "aws.events":
        # CloudWatch Event のやつ
        cronAction = CronAction(dynamo)
        asyncio.run(cronAction.execute())
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
    if (
        isinstance(body, dict)
        and body.get("events", [{"type": ""}])[0]["type"] == "follow"
    ):
        if body["events"][0]["source"]["type"] == "user":
            user_id = body["events"][0]["source"]["userId"]
            add_user(user_id)
    # LINE unfollow user
    if (
        isinstance(body, dict)
        and body.get("events", [{"type": ""}])[0]["type"] == "unfollow"
    ):
        if body["events"][0]["source"]["type"] == "user":
            user_id = body["events"][0]["source"]["userId"]
            delete_user(user_id)

    text = ""
    # LINE webhook
    if isinstance(body, dict):
        for event in body.get("events", []):
            TOKEN = event.get("replyToken", "")
            text = event.get("message", {}).get("text")
            # postback の場合はメソッドのデフォルトで動作するように設定
            if event.get("postback", {}).get("data"):
                text = event["postback"]["data"]
    text = text.replace("　", " ").replace("\n", " ")
    args = text.split(" ")
    replyAction = ReplyAction(dynamo, USER_ID)
    if len(args) > 0 and args[0] == "コマンド":
        reply(replyAction._help())
    elif len(args) > 0 and args[0] == "定期無効":
        toggle_teiki(False)
        reply_message("定期実行を無効にしました")
    elif len(args) > 0 and args[0] == "定期有効":
        toggle_teiki(True)
        reply_message("定期実行を有効にしました")
    elif len(args) > 0 and args[0] == "1有効":
        toggle_ait(True)
        reply_message("アットマークITランキングを有効にしました")
    elif len(args) > 0 and args[0] == "1無効":
        toggle_ait(False)
        reply_message("アットマークITランキングを無効にしました")
    elif len(args) > 0 and args[0] == "2有効":
        toggle_ait_new_all(True)
        reply_message("アットマークITの全フォーラムの新着記事を有効にしました")
    elif len(args) > 0 and args[0] == "2無効":
        toggle_ait_new_all(False)
        reply_message("アットマークITの全フォーラムの新着記事を無効にしました")
    elif len(args) > 0 and args[0] == "3有効":
        toggle_smart_jp(True)
        reply_message("スマートジャパンの新着記事を有効にしました")
    elif len(args) > 0 and args[0] == "3無効":
        toggle_smart_jp(False)
        reply_message("スマートジャパンの新着記事を無効にしました")
    elif len(args) > 0 and args[0] == "4有効":
        toggle_itmedia_news(True)
        reply_message("ITmedia NEWS 最新記事一覧を有効にしました")
    elif len(args) > 0 and args[0] == "4無効":
        toggle_itmedia_news(False)
        reply_message("ITmedia NEWS 最新記事一覧を無効にしました")
    elif len(args) > 0 and args[0] == "5有効":
        toggle_zdjapan(True)
        reply_message("ZDNet Japan 最新情報 総合を有効にしました")
    elif len(args) > 0 and args[0] == "5無効":
        toggle_zdjapan(False)
        reply_message("ZDNet Japan 最新情報 総合を無効にしました")
    elif len(args) > 0 and args[0] == "6有効":
        toggle_uxmilk(True)
        reply_message("UX MILK の最新ニュースを有効にしました")
    elif len(args) > 0 and args[0] == "6無効":
        toggle_uxmilk(False)
        reply_message("UX MILK の最新ニュースを無効にしました")
    elif len(args) > 0 and args[0] == "7有効":
        toggle_techTarget(True)
        reply_message("TechTarget Japanの最新記事一覧を有効にしました")
    elif len(args) > 0 and args[0] == "7無効":
        toggle_techTarget(False)
        reply_message("TechTarget Japanの最新記事一覧を無効にしました")
    else:
        func = replyAction._method_search("".join(args))
        if func:
            LOGGER.info(f"method: {func}, param: {args[1:]}")
            asyncio.run(reply_action(replyAction, func, args[1:]))

    payload = {
        "messages": [
            {"type": "text", "text": "200 OK"},
        ],
    }

    ret = {
        "statusCode": "200",
        "body": json.dumps(payload, ensure_ascii=False),
        "headers": {
            "Content-Type": "application/json",
        },
    }
    LOGGER.info(f"[RETURN] {ret}")
    LOGGER.info("--LAMBDA END--")
    return ret


async def reply_action(replyAction, func, args):
    """メソッドでasyncを使っているため切り出し."""
    message = await replyAction.executeAction(func, args)
    if message:
        reply(message)
