"""応答メッセージをするメソッド群."""
import logging
import os
import re

from Actions import Actions
from decos import log
from message import create_content, create_content2, create_footer, create_header, create_message

# 応答メッセージとして許容するメソッド群
ITEM = {
    "aitNewAll": {
        "name": "アットマークITの全フォーラムの新着記事",
        "must": ["アットマークIT", "新着"],
    },
    "aitRanking": {
        "name": "アットマークITの本日の総合ランキング",
        "must": ["アットマークIT", "ランキング"],
    },
    "itmediaNews": {
        "name": "ITmedia NEWS 最新記事一覧",
        "must": ["ITmedia", "最新"],
    },
    "jpcertAlert": {
        "name": "脆弱性関連情報",
        "must": ["脆弱性"],
    },
    "jpcertNotice": {
        "name": "注意喚起",
        "must": ["注意喚起"],
    },
    "lunch": {
        "name": "ランチ検索",
        "must": ["ランチ", "検索"],
    },
    "nomitai": {
        "name": "居酒屋検索",
        "must": ["居酒屋", "検索"],
    },
    "qiita": {
        "name": "Qiitaの新着",
        "must": ["Qiita", "新着"],
    },
    "smartJp": {
        "name": "スマートジャパンの新着記事",
        "must": ["スマートジャパン", "新着"],
    },
    "techCrunchJapan": {
        "name": "Tech Crunch Japanのニュース一覧",
        "must": ["Tech", "Crunch", "ニュース"],
    },
    "uxmilk": {
        "name": "UX MILKのニュース一覧",
        "must": ["UX", "MILK", "ニュース"],
    },
    "weeklyReport": {
        "name": "JPCERT Weekly Report",
        "must": ["JPCERT", "Report"],
    },
    "zdjapan": {
        "name": "ZDNet Japan 最新情報 総合",
        "must": ["ZDNet", "最新"],
    },
    "teiki": {
        "name": "定期実行確認",
        "must": ["定期", "確認"],
    },
    "techTarget": {
        "name": "TechTarget Japanの最新記事一覧",
        "must": ["Tech", "Target"],
    },
}

LOGGER = logging.getLogger(name="Lambda")


class ReplyAction:
    """やりたい処理を定義."""

    def __init__(self, dynamo, user_id):
        self.dynamo = dynamo
        self.user_id = user_id
        self.HOTPEPPER = os.environ.get("hotpepper")
        self.HEADER = {
            "User-agent": """\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"""
        }

    @classmethod
    @log(LOGGER)
    def _help(cls):
        """メソッド一覧."""
        methods = [a for a in dir(Actions) if "_" not in a]
        header = create_header("メソッド一覧", None)
        contents = []
        for _method in methods:
            description = re.sub(" {1,}", "", getattr(Actions, _method).__doc__)
            args = re.split(r"\.\n", description)
            title = args[0]
            # 末尾の改行も消している
            description = "\n".join(("".join(args[1:])).split("\n")[1:]).rstrip()
            # Returnsは不要
            description = description.split("\n\n")[0]
            label = ITEM.get(_method, {}).get("name", title)
            content = {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "4px",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "color": "#35393c",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": description,
                        "size": "xs",
                        "color": "#8C8C8C",
                        "wrap": True,
                    },
                ],
                "action": {
                    "type": "postback",
                    "label": label,
                    "data": label,
                    "displayText": label,
                },
                "flex": 0,
            }
            contents.append(content)
        # 定期実行だけActionsではないので足す
        description = re.sub(" {1,}", "", getattr(cls, "teiki").__doc__)
        args = re.split(r"\.\n", description)
        title = args[0]
        # 末尾の改行も消している
        description = "\n".join(("".join(args[1:])).split("\n")[1:]).rstrip()
        # Returnsは不要
        description = description.split("\n\n")[0]
        label = ITEM.get("teiki", {}).get("name", title)
        content = {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "4px",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "color": "#35393c",
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": description,
                    "size": "xs",
                    "color": "#8C8C8C",
                    "wrap": True,
                },
            ],
            "action": {
                "type": "postback",
                "label": label,
                "data": label,
                "displayText": label,
            },
            "flex": 0,
        }
        contents.append(content)

        message = create_message(header, contents, None)

        return message

    @log(LOGGER)
    def _method_search(self, text):
        """対象のメソッドがあればそのメソッド名を返す."""
        for key, value in ITEM.items():
            check = 0
            for must in value["must"]:
                if must in text:
                    check += 1
            if check == len(value["must"]):
                return key

    @log(LOGGER)
    async def executeAction(self, func_name: str, args: list) -> dict:
        """メソッドを実行して応答メッセージを作成して返す."""
        if func_name == "teiki":
            return self.teiki()
        contents = []
        data = await getattr(Actions, func_name)(args)
        if data is None:
            # エラーの場合
            contents = [create_content("エラーが発生したため取得できませんでした", None)]
        elif len(data) == 0:
            # 検索結果なし
            contents = [create_content("取得できるものがありませんでした", None)]
        else:
            for d in data:
                content = create_content(d["title"], d["link"])
                contents.append(content)
        header = create_header(ITEM.get(func_name, {}).get("name"), None)
        footer = None
        if func_name in ["lunch", "nomitai"]:
            footer = create_footer("Powered by ホットペッパー Webサービス")
        return create_message(header, contents, footer)

    @log(LOGGER)
    def teiki(self) -> None:
        """定期実行.

        有効にしたら、毎日正午にニュース等を取得します。
        有効かどうかをチェックするには、このメソッドを実行してください。
        """
        header = create_header("定期実行の確認", None)
        contents = []
        for item in self.dynamo.scan(**{"TableName": "users"})["Items"]:
            if item["user_id"]["S"] == self.user_id:
                # 定期実行
                is_enable = True if item.get("enabled", {}).get("BOOL", False) else False
                postback = "定期無効" if is_enable else "定期有効"
                contents.append(create_content2("定期実行", is_enable, postback))
                # アットマークITランキング
                is_enable = True if item.get("ait_enabled", {}).get("BOOL", False) else False
                postback = "1無効" if is_enable else "1有効"
                contents.append(create_content2("(1)アットマークITランキング", is_enable, postback))
                # アットマークIT新着
                is_enable = True if item.get("ait_new_all_enabled", {}).get("BOOL", False) else False
                postback = "2無効" if is_enable else "2有効"
                contents.append(create_content2("(2)アットマークITの全フォーラムの新着記事", is_enable, postback))
                # スマートジャパン新着
                is_enable = True if item.get("smart_jp_enabled", {}).get("BOOL", False) else False
                postback = "3無効" if is_enable else "3有効"
                contents.append(create_content2("(3)スマートジャパンの新着記事", is_enable, postback))
                # ITmedia NEWS新着
                is_enable = True if item.get("itmedia_news_enabled", {}).get("BOOL", False) else False
                postback = "4無効" if is_enable else "4有効"
                contents.append(create_content2("(4)ITmedia NEWS 最新記事一覧", is_enable, postback))
                # ZDNet Japan新着
                is_enable = True if item.get("zdjapan_enabled", {}).get("BOOL", False) else False
                postback = "5無効" if is_enable else "5有効"
                contents.append(create_content2("(5)ZDNet Japan 最新情報 総合", is_enable, postback))
                # UX MILK新着
                is_enable = True if item.get("uxmilk", {}).get("BOOL", False) else False
                postback = "6無効" if is_enable else "6有効"
                contents.append(create_content2("(6)UX MILK の最新ニュース", is_enable, postback))
                # TechTarget Japan最新記事
                is_enable = True if item.get("techTarget", {}).get("BOOL", False) else False
                postback = "7無効" if is_enable else "7有効"
                contents.append(create_content2("(7)TechTarget Japanの最新記事一覧", is_enable, postback))
        footer = create_footer(
            """\
定期実行が無効の場合、有効なものがあってもプッシュ通知されません。
定期実行が有効の場合、JPCERTの最新情報はオフにできません。
タップすると有効・無効を切り替えます。"""
        )
        return create_message(header, contents, footer)
