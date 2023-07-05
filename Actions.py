import datetime
import json
import logging
import os
import traceback
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
from decos import log


LOGGER = logging.getLogger(name="Lambda")

# 日本時間に調整
NOW = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
# 1日と3分前を前日とする
YESTERDAY = NOW - datetime.timedelta(days=1) - datetime.timedelta(minutes=3)
YESTERDAY = datetime.datetime(
    YESTERDAY.year,
    YESTERDAY.month,
    YESTERDAY.day,
    YESTERDAY.hour,
    YESTERDAY.minute,
    YESTERDAY.second,
)
HEADER = {
    "User-agent": """\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"""
}


def get_text(item: list, tag_name: str) -> str:
    """XMLのタグ名を基に文字列を取得.

    タグ名は小文字に置き換えて検索します。
    """
    for elem in item:
        if tag_name in elem.tag.lower():
            return elem.text
    return ""


class Actions:
    @classmethod
    @log(LOGGER)
    async def aitNewAll(cls, *_) -> list:
        """アットマークITの全フォーラムの新着記事.

        アットマークITの全フォーラムの新着記事を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://rss.itmedia.co.jp/rss/2.0/ait.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    if get_text(child, "title").startswith("PR:"):
                        continue
                    if get_text(child, "title").startswith("PR： "):
                        continue
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = {
                            "title": get_text(child, "title"),
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def aitRanking(cls, *_) -> list:
        """アットマークITの本日の総合ランキング.

        アットマークITの本日の総合ランキングを取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://www.atmarkit.co.jp/json/ait/rss_rankindex_all_day.json"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            json_str = (
                res.content.decode("sjis")
                .replace("rankingindex(", "")
                .replace(")", "")
                .replace("'", '"')
            )
            json_data = json.loads(json_str)
            for item in json_data["data"]:
                if len(contents) >= 10:
                    break
                if item:
                    content = {
                        "title": item["title"].replace(" ", ""),
                        "link": item["link"],
                    }
                    contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def itmediaNews(cls, *_) -> list:
        """ITmedia NEWS 最新記事一覧.

        ITmedia NEWSの最新記事一覧を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = {
                            "title": get_text(child, "title"),
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def techTarget(cls, *_) -> list:
        """TechTarget Japanの最新記事一覧.

        TechTarget Japanの最新記事一覧を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://rss.itmedia.co.jp/rss/2.0/techtarget.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    title = get_text(child, "title")
                    if YESTERDAY <= pub_date and not title.startswith("PR："):
                        content = {
                            "title": title,
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def jpcertAlert(cls, *_) -> list:
        """脆弱性関連情報.

        JPCERTで当日発表された脆弱性関連情報を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://www.jpcert.or.jp"
        contents = []
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            items = jpcert.select("div.container")
            for data in items:
                if data.select("h3") and data.select("h3")[0].text == "脆弱性関連情報":
                    for li in data.select("ul.list>li"):
                        published = (
                            li.select("a")[0].select("span.left_area")[0].text.strip()
                        )
                        dt_published = datetime.datetime.strptime(
                            published, "%Y-%m-%d %H:%M"
                        )
                        title = li.select("a")[0].select("span.right_area")[0].text
                        if YESTERDAY <= dt_published:
                            link = li.select("a")[0].get("href")
                            content = {
                                "title": title,
                                "link": link,
                            }
                            contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def jpcertNotice(cls, *_) -> dict:
        """注意喚起.

        JPCERTで当日発表された注意喚起を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://www.jpcert.or.jp"
        today = NOW.strftime("%Y-%m-%d")
        contents = []
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            items = jpcert.select("div.container")
            for data in items:
                if data.select("h3") and data.select("h3")[0].text == "注意喚起":
                    for li in data.select("ul.list>li"):
                        published = li.select("a")[0].select("span.left_area")[0].text
                        title = li.select("a")[0].select("span.right_area")[0].text
                        if today in published:
                            link = url + li.select("a")[0].get("href")
                            content = {
                                "title": f"{today} {title}",
                                "link": link,
                            }
                            contents.append(content)
                        if YESTERDAY.strftime("%Y-%m-%d") in published:
                            link = url + li.select("a")[0].get("href")
                            content = {
                                "title": f"{YESTERDAY.strftime('%Y-%m-%d')} {title}",
                                "link": link,
                            }
                            contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def lunch(cls, args: list) -> list:
        """ランチ営業店舗検索.

        スペース区切りもしくは改行区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        _param = {
            "key": os.environ.get("hotpepper"),
            "large_service_area": "SS10",  # 関東
            "range": "3",
            "order": "2",
            "type": "lite",
            "format": "json",
            "count": "100",
            "lunch": "1",
        }
        if not args or len(args) == 1:
            _param["lat"] = os.environ["default_lat"]
            _param["lng"] = os.environ["default_lng"]
        if len(args) > 0:
            _param["keyword"] = " ".join(list(args))
        hotpepper = requests.get(
            "http://webservice.recruit.co.jp/hotpepper/gourmet/v1/",
            params=_param,
            headers=HEADER,
        )
        contents = []
        shops = hotpepper.json()["results"]["shop"]
        if len(shops) > 0:
            for shop in shops:
                content = {
                    "title": shop["name"],
                    "link": shop["urls"]["pc"],
                }
                contents.append(content)
        else:
            content = {
                "title": "検索結果がありません",
                "link": None,
            }
            contents.append(content)
        return contents

    @classmethod
    @log(LOGGER)
    async def nomitai(cls, args: list) -> list:
        """居酒屋検索.

        スペース区切りもしくは改行区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        _param = {
            "key": os.environ.get("hotpepper"),
            "large_service_area": "SS10",  # 関東
            "range": "5",
            "order": "2",
            "type": "lite",
            "format": "json",
            "count": "100",
        }
        if not args or len(args) == 1:
            _param["lat"] = os.environ["default_lat"]
            _param["lng"] = os.environ["default_lng"]
            if not args:
                # デフォルトは居酒屋
                _param["genre"] = "G001"
        if len(args) > 0:
            _param["keyword"] = " ".join(list(args))
        if len(args) >= 2:
            # 範囲を絞る
            _param["range"] = 3

        hotpepper = requests.get(
            "http://webservice.recruit.co.jp/hotpepper/gourmet/v1/",
            params=_param,
            headers=HEADER,
        )
        contents = []
        shops = hotpepper.json()["results"]["shop"]
        if len(shops) > 0:
            for shop in shops:
                content = {
                    "title": shop["name"],
                    "link": shop["urls"]["pc"],
                }
                contents.append(content)
        else:
            content = {
                "title": "検索結果がありません",
                "link": None,
            }
            contents.append(content)
        return contents

    @classmethod
    @log(LOGGER)
    async def qiita(cls, *_) -> list:
        """Qiita新着記事取得.

        Qiitaの新着記事を3件取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        res = requests.get(
            "https://qiita.com/api/v2/items?page=1&per_page=3", headers=HEADER
        )
        data = res.json()
        contents = []
        for d in data:
            content = {
                "title": d["title"],
                "link": d["url"],
            }
            contents.append(content)
        return contents

    @classmethod
    @log(LOGGER)
    async def smartJp(cls, *_) -> list:
        """スマートジャパンの新着記事.

        スマートジャパンの新着記事を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://rss.itmedia.co.jp/rss/2.0/smartjapan.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    if get_text(child, "title").startswith("PR:"):
                        continue
                    if get_text(child, "title").startswith("PR： "):
                        continue
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = {
                            "title": get_text(child, "title"),
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def uxmilk(cls, *_) -> list:
        """UX MILKのニュース一覧.

        UX MILKからニュースを取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://uxmilk.jp/feed"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = {
                            "title": get_text(child, "title"),
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def weeklyReport(cls, *_) -> list:
        """JPCERT Weekly Report.

        JPCERT から Weekly Report を取得します。
        水曜日とかじゃないと何も返ってきません。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "https://www.jpcert.or.jp"
        today = NOW.strftime("%Y-%m-%d")
        contents = []
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            whatsdate = jpcert.select("a.fl")[0].text.replace("号", "")
            if today == whatsdate:
                wkrp = jpcert.select("div.contents")[0].select("li")
                for i, item in enumerate(wkrp, start=1):
                    content = {
                        "title": f"{i}. {item.text}",
                        "link": f"{url}{jpcert.select('a.fl')[0].get('href')}#{i}",
                    }
                    contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents

    @classmethod
    @log(LOGGER)
    async def zdjapan(cls, *_) -> list:
        """ZDNet Japan 最新情報 総合.

        ZDNet Japanから最新情報を取得します。

        Returns:
            list: 辞書を格納した配列を返す。エラー発生時、Noneを返す
            [
                {'title': '<記事のタイトル>', 'link': '<記事のリンク>'}, ...
            ]
        """
        url = "http://feeds.japan.zdnet.com/rss/zdnet/all.rdf"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        contents = []
        try:
            res = requests.get(url, headers=HEADER)
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root:
                if "item" in child.tag.lower():
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "date")[0:19], "%Y-%m-%dT%H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = {
                            "title": get_text(child, "title"),
                            "link": get_text(child, "link"),
                        }
                        contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
        return contents
