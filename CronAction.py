"""cron実行するメソッド群.

レスポンスは以下の形式で返す。

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

import datetime
import json
import logging
import os

import requests

from Actions import Actions
from decos import log
from message import create_content, create_header, create_message


# 配信メッセージとして許容するメソッド群
ITEM: dict[str, dict[str, str | bool]] = {
    "aitNewAll": {
        "name": "アットマークITの全フォーラムの新着記事",
        "must": False,
    },
    "aitRanking": {
        "name": "アットマークITの本日の総合ランキング",
        "must": False,
    },
    "itmediaNews": {
        "name": "ITmedia NEWS 最新記事一覧",
        "must": False,
    },
    "smartJp": {
        "name": "スマートジャパンの新着記事",
        "must": False,
    },
    "techCrunchJapan": {
        "name": "Tech Crunch Japanのニュース一覧",
        "must": False,
    },
    "zdjapan": {
        "name": "ZDNet Japan 最新情報 総合",
        "must": False,
    },
    "techTarget": {
        "name": "TechTarget Japanの最新記事一覧",
        "must": False,
    },
    "jpcertAlert": {
        "name": "脆弱性関連情報",
        "must": True,
    },
    "jpcertNotice": {
        "name": "注意喚起",
        "must": True,
    },
    "weeklyReport": {
        "name": "JPCERT Weekly Report",
        "must": True,
    },
}

LOGGER = logging.getLogger(name="Lambda")

# Webhook には含めない配信
WEBHOOK_EXCLUDED = {"jpcertAlert", "jpcertNotice", "weeklyReport"}


def push(user_id: str, message: dict) -> None:
    """プッシュ通知する.

    Args:
        user_id (str): 送信先のユーザー ID.
        message (dict): 送信するメッセージ.
    """
    if not user_id:
        # 送信先がなければ何もしない
        return
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/push"
    payload = {"to": user_id, "messages": [message]}
    LOGGER.info(f"[REQUEST] param: {json.dumps(payload, ensure_ascii=False)}")
    res = requests.post(url, json=payload, headers=headers)
    LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


def build_news_for_webhook(value: dict, data: list | None, name: str) -> dict | None:
    """Webhook 用に、サイトごとの記事一覧を作る.

    配信対象外、Webhook の除外対象、または記事がなければ None を返す。

    Args:
        value (dict): ユーザーの配信設定.
        data (list | None): サイトから取得した記事の配列.
        name (str): 配信対象の識別子.
    """
    if name in WEBHOOK_EXCLUDED:
        return None
    if not ((value.get(name, False) or ITEM[name]["must"]) and data is not None and len(data) > 0):
        return None
    items = [{"title": article["title"], "url": article["link"]} for article in data]
    return {"site": ITEM[name]["name"], "items": items}


def notify_webhook(user_id: str, news: list) -> None:
    """特定ユーザー向けに別 Webhook へ送る.

    送信失敗しても LINE 配信は止めない。

    Args:
        user_id (str): 送信先のユーザー ID.
        news (list): サイトごとの記事一覧.
    """
    if not news:
        return
    url = os.environ["webhook_url"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['webhook_token']}",
    }
    today = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=9)).strftime("%Y/%m/%d")
    payload = {"to": user_id, "date": today, "news": news}
    LOGGER.info(f"[WEBHOOK] param: {json.dumps(payload, ensure_ascii=False)}")
    try:
        res = requests.post(url, json=payload, timeout=10, headers=headers)
        LOGGER.info(f"[WEBHOOK] [STATUS]{res.status_code} [CONTENT]{res.content}")
    except requests.RequestException:
        LOGGER.exception("[WEBHOOK] request failed")


def build_contents(value: dict, data: list, name: str) -> list:
    """LINEの配信メッセージのbody部に挿入するための要素を生成する.

    特になければ空の配列を返す。

    Args:
        value (dict): ユーザーの配信設定.
        data (list): サイトから取得した記事の配列.
        name (str): 配信対象の識別子.

    Returns:
        list: bodyのcontentsに格納する要素の配列
    """
    contents = []
    if (value.get(name, False) or ITEM[name]["must"]) and data is not None and len(data) > 0:
        contents.append(create_header(ITEM[name]["name"], None))
        for d in data:
            contents.append(create_content(d["title"], d["link"]))
    return contents


class CronAction:
    """Cron アクションクラス."""

    def __init__(self, dynamo):
        """コンストラクタ.

        Args:
            dynamo: DynamoDB クライアント.
        """
        self.dynamo = dynamo

    @log(LOGGER)
    async def execute(self):
        """ユーザーごとにまとめて配信する."""
        user_settings = {}

        for item in self.dynamo.scan(TableName="users")["Items"]:
            # 配信を有効にしているユーザーの情報を取得
            if item["enabled"]["BOOL"]:
                user_settings[item["user_id"]["S"]] = {
                    "aitRanking": item.get("ait_enabled", {}).get("BOOL", False),
                    "aitNewAll": item.get("ait_new_all_enabled", {}).get("BOOL", False),
                    "itmediaNews": item.get("itmedia_news_enabled", {}).get("BOOL", False),
                    "smartJp": item.get("smart_jp_enabled", {}).get("BOOL", False),
                    "zdjapan": item.get("zdjapan_enabled", {}).get("BOOL", False),
                    "techTarget": item.get("techTarget", {}).get("BOOL", False),
                }
        aitRanking = await Actions.aitRanking()
        aitNewAll = await Actions.aitNewAll()
        itmediaNews = await Actions.itmediaNews()
        smartJp = await Actions.smartJp()
        zdjapan = await Actions.zdjapan()
        techTarget = await Actions.techTarget()
        jpcertAlert = await Actions.jpcertAlert()
        jpcertNotice = await Actions.jpcertNotice()
        weeklyReport = await Actions.weeklyReport()

        sources = [
            ("aitRanking", aitRanking),
            ("aitNewAll", aitNewAll),
            ("itmediaNews", itmediaNews),
            ("smartJp", smartJp),
            ("zdjapan", zdjapan),
            ("techTarget", techTarget),
            ("jpcertAlert", jpcertAlert),
            ("jpcertNotice", jpcertNotice),
            ("weeklyReport", weeklyReport),
        ]
        for user_id, value in user_settings.items():
            # ユーザーごとにコンテンツを生成し、配信
            contents = []
            news_for_webhook = []
            for name, data in sources:
                contents.extend(build_contents(value, data, name))
                site_news = build_news_for_webhook(value, data, name)
                if site_news:
                    news_for_webhook.append(site_news)
            header = create_header("定期実行", None)
            if len(contents) > 0:
                push(user_id, create_message(header, contents, None))
                notify_webhook(user_id, news_for_webhook)
