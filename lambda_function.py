"""LINE bot 用の AWS Lambda 関数.

DynamoDB の使い方は以下。
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

from CronAction import CronAction
from mylogger import begin_log_scope, build_stream_handler
from ReplyAction import ReplyAction


LOGGER = logging.getLogger(name="Lambda")
LOGGER.setLevel(logging.DEBUG)
# Lambda のルートロガーへ伝播させると、CloudWatch に同じ行が 2 回出る.
LOGGER.propagate = False
LOGGER.addHandler(build_stream_handler())

dynamo = boto3.client("dynamodb")

# def respond(err, res=None):
#     return {
#         "statusCode": "400" if err else "200",
#         "body": err.message if err else json.dumps(res),
#         "headers": {
#             "Content-Type": "application/json",
#         },
#     }


def reply_message(message: str, reply_token: str) -> None:
    """文字列を LINE のテキストメッセージとして返信する.

    渡した文字列を {"type": "text", "text": message} に包んで Reply API へ送る.
    設定変更の完了通知など、一文で足りる応答に使う.

    Args:
        message (str): 返信する本文
        reply_token (str): LINE の Reply API で必要なトークン
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/reply"
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message,
            }
        ],
    }
    LOGGER.info(f"[REQUEST] {url}, param: {json.dumps(payload, ensure_ascii=False)}")
    res = requests.post(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def reply(message: dict, reply_token: str) -> None:
    """組み立て済みの LINE メッセージを返信する.

    Flex Message など、すでに LINE のメッセージオブジェクトになっている dict を Reply API へそのまま送る.
    コマンド一覧や記事一覧の応答に使う.

    Args:
        message (dict): LINE のメッセージオブジェクト
        reply_token (str): LINE の Reply API で必要なトークン
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/reply"
    payload = {"replyToken": reply_token, "messages": [message]}
    LOGGER.info(f"[REQUEST] {url}, param: {json.dumps(payload, ensure_ascii=False)}")
    res = requests.post(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def add_user(user_id: str) -> None:
    """ユーザー追加.

    Args:
        user_id (str): 追加するユーザーID
    """
    param = {
        "TableName": "users",
        "Item": {"user_id": {"S": user_id}, "enabled": {"BOOL": False}},
    }
    LOGGER.info(f"[DynamoDB insert] user_id: {user_id}")
    dynamo.put_item(**param)


def update_user(user_id: str, params: dict) -> None:
    """ユーザー情報更新.

    Args:
        user_id (str): 対象のユーザーID
        params (dict): ユーザーに対して登録するパラメータを指定する
            {
                "enabled": {"BOOL": True},
                ...
            }
    """
    items = {}
    for item in dynamo.scan(TableName="users")["Items"]:
        if user_id == item["user_id"]["S"]:
            items.update(item)
    # 配信をやめた項目のキーは洗い替えで落とす
    for obsolete in ("uxmilk", "tech_crunch_jp_enabled", "tech_republic_jp_enabled"):
        items.pop(obsolete, None)
    param = {"TableName": "users", "Item": items}
    param["Item"].update(params)
    # dynamo.update_item(**param)
    dynamo.put_item(**param)


def delete_user(user_id: str) -> None:
    """ユーザー削除.

    Args:
        user_id (str): 削除するユーザーID
    """
    param = {"TableName": "users", "Key": {"user_id": {"S": user_id}}}
    dynamo.delete_item(**param)


def toggle_teiki(enabled: bool, user_id: str) -> None:
    """定期実行の有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_ait(enabled: bool, user_id: str) -> None:
    """アットマークITのランキングの定期実行有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"ait_enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_ait_new_all(enabled: bool, user_id: str) -> None:
    """アットマークITの新着の定期実行有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"ait_new_all_enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_smart_jp(enabled: bool, user_id: str) -> None:
    """スマートジャパンの新着の定期実行有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"smart_jp_enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_itmedia_news(enabled: bool, user_id: str) -> None:
    """ITMedia NEWSの新着の定期実行有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"itmedia_news_enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_zdjapan(enabled: bool, user_id: str) -> None:
    """ZDNet Japanの新着の定期実行p有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"zdjapan_enabled": {"BOOL": enabled}}
    update_user(user_id, params)


def toggle_techTarget(enabled: bool, user_id: str) -> None:
    """TechTargetの新着の定期実行有効化、もしくは無効化.

    Args:
        enabled (bool): True で有効化、False で無効化
        user_id (str): 対象のユーザーID
    """
    params = {"techTarget": {"BOOL": enabled}}
    update_user(user_id, params)


def lambda_handler(event, context):  # noqa: C901
    """Demonstrates a simple HTTP endpoint using API Gateway. You have full
    access to the request and response payload, including headers and
    status code.

    To scan a DynamoDB table, make a GET request with the TableName as a
    query string parameter. To put, update, or delete an item, make a POST,
    PUT, or DELETE request respectively, passing in the payload to the
    DynamoDB API as a JSON body.
    """
    begin_log_scope()
    LOGGER.info("--LAMBDA START--")
    LOGGER.info(f"event: {json.dumps(event)}")
    LOGGER.info(f"context: {context}")
    user_id = ""
    try:
        body = json.loads(event.get("body"))
        user_id = body.get("events", [])[0]["source"]["userId"]
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
        and body["events"][0]["source"]["type"] == "user"
    ):
        user_id = body["events"][0]["source"]["userId"]
        add_user(user_id)
    # LINE unfollow user
    if (
        isinstance(body, dict)
        and body.get("events", [{"type": ""}])[0]["type"] == "unfollow"
        and body["events"][0]["source"]["type"] == "user"
    ):
        user_id = body["events"][0]["source"]["userId"]
        delete_user(user_id)

    text = ""
    # LINE webhook
    if isinstance(body, dict):
        for event in body.get("events", []):
            reply_token = event.get("replyToken", "")
            text = event.get("message", {}).get("text")
            # postback の場合はメソッドのデフォルトで動作するように設定
            if event.get("postback", {}).get("data"):
                text = event["postback"]["data"]
    text = text.replace("　", " ").replace("\n", " ")
    args = text.split(" ")
    replyAction = ReplyAction(dynamo, user_id)
    if len(args) > 0 and args[0] == "コマンド":
        reply(replyAction._help(), reply_token)
    elif len(args) > 0 and args[0] == "定期無効":
        toggle_teiki(False, user_id)
        reply_message("定期実行を無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "定期有効":
        toggle_teiki(True, user_id)
        reply_message("定期実行を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "1有効":
        toggle_ait(True, user_id)
        reply_message("アットマークITランキングを有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "1無効":
        toggle_ait(False, user_id)
        reply_message("アットマークITランキングを無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "2有効":
        toggle_ait_new_all(True, user_id)
        reply_message("アットマークITの全フォーラムの新着記事を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "2無効":
        toggle_ait_new_all(False, user_id)
        reply_message("アットマークITの全フォーラムの新着記事を無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "3有効":
        toggle_smart_jp(True, user_id)
        reply_message("スマートジャパンの新着記事を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "3無効":
        toggle_smart_jp(False, user_id)
        reply_message("スマートジャパンの新着記事を無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "4有効":
        toggle_itmedia_news(True, user_id)
        reply_message("ITmedia NEWS 最新記事一覧を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "4無効":
        toggle_itmedia_news(False, user_id)
        reply_message("ITmedia NEWS 最新記事一覧を無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "5有効":
        toggle_zdjapan(True, user_id)
        reply_message("ZDNet Japan 最新情報 総合を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "5無効":
        toggle_zdjapan(False, user_id)
        reply_message("ZDNet Japan 最新情報 総合を無効にしました", reply_token)
    elif len(args) > 0 and args[0] == "6有効":
        toggle_techTarget(True, user_id)
        reply_message("TechTarget Japanの最新記事一覧を有効にしました", reply_token)
    elif len(args) > 0 and args[0] == "6無効":
        toggle_techTarget(False, user_id)
        reply_message("TechTarget Japanの最新記事一覧を無効にしました", reply_token)
    else:
        func = replyAction._method_search("".join(args))
        if func:
            LOGGER.info(f"method: {func}, param: {args[1:]}")
            asyncio.run(reply_action(replyAction, func, args[1:], reply_token))

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


async def reply_action(replyAction: ReplyAction, func: str, args: list, reply_token: str):
    """メソッドでasyncを使っているため切り出し.

    Args:
        replyAction (ReplyAction): ReplyActionのインスタンス
        func (str): 実行するメソッド名
        args (list): メソッドに渡す引数のリスト
        reply_token (str): LINE の Reply API で必要なトークン
    """
    message = await replyAction.executeAction(func, args)
    if message:
        reply(message, reply_token)
