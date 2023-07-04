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
import json
import logging
import os
import requests
from decos import log
from message import create_content, create_header, create_message
from Actions import Actions


# 配信メッセージとして許容するメソッド群
ITEM = {
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
    "uxmilk": {
        "name": "UX MILKのニュース一覧",
        "must": False,
    },
    "zdjapan": {
        "name": "ZDNet Japan 最新情報 総合",
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


def push(user_list: list, message: dict) -> None:
    """プッシュ通知する."""
    if not user_list:
        # 送信先がなければ何もしない
        return
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = "https://api.line.me/v2/bot/message/multicast"
    payload = {"to": user_list, "messages": [message]}
    LOGGER.info(f"[REQUEST] param: {json.dumps(payload)}")
    res = requests.post(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}"
    )


def build_contents(value: dict, data: list, name: str) -> list:
    """LINEの配信メッセージのbody部に挿入するための要素を生成する.

    特になければ空の配列を返す。

    Returns:
        list: bodyのcontentsに格納する要素の配列
    """
    contents = []
    if value.get(name, False) or ITEM[name]["must"]:
        if data is not None and len(data) > 0:
            contents.append(create_header(ITEM[name]["name"], None))
            for d in data:
                contents.append(create_content(d["title"], d["link"]))
    return contents


class CronAction:
    def __init__(self, dynamo):
        self.dynamo = dynamo

    @log(LOGGER)
    async def execute(self):
        """ユーザーごとにまとめて配信する."""
        user_settings = {}

        for item in self.dynamo.scan(**{"TableName": "users"})["Items"]:
            # 配信を有効にしているユーザーの情報を取得
            if item["enabled"]["BOOL"]:
                user_settings[item["user_id"]["S"]] = {
                    "aitRanking": item.get("ait_enabled", {}).get("BOOL", False),
                    "aitNewAll": item.get("ait_new_all_enabled", {}).get("BOOL", False),
                    "smartJp": item.get("smart_jp_enabled", {}).get("BOOL", False),
                    "itmediaNews": item.get("itmedia_news_enabled", {}).get(
                        "BOOL", False
                    ),
                    "zdjapan": item.get("zdjapan_enabled", {}).get("BOOL", False),
                    "uxmilk": item.get("uxmilk", {}).get("BOOL", False),
                }
        aitRanking = await Actions.aitRanking()
        aitNewAll = await Actions.aitNewAll()
        itmediaNews = await Actions.itmediaNews()
        jpcertAlert = await Actions.jpcertAlert()
        jpcertNotice = await Actions.jpcertNotice()
        smartJp = await Actions.smartJp()
        uxmilk = await Actions.uxmilk()
        weeklyReport = await Actions.weeklyReport()
        zdjapan = await Actions.zdjapan()

        for user_id, value in user_settings.items():
            # ユーザーごとにコンテンツを生成し、配信
            contents = []
            contents.extend(build_contents(value, aitRanking, "aitRanking"))
            contents.extend(build_contents(value, aitNewAll, "aitNewAll"))
            contents.extend(build_contents(value, itmediaNews, "itmediaNews"))
            contents.extend(build_contents(value, smartJp, "smartJp"))
            contents.extend(build_contents(value, uxmilk, "uxmilk"))
            contents.extend(build_contents(value, zdjapan, "zdjapan"))
            contents.extend(build_contents(value, jpcertAlert, "jpcertAlert"))
            contents.extend(build_contents(value, jpcertNotice, "jpcertNotice"))
            contents.extend(build_contents(value, weeklyReport, "weeklyReport"))
            header = create_header("定期実行", None)
            if len(contents) > 0:
                push([user_id], create_message(header, contents, None))
