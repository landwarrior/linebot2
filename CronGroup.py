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
import traceback
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from decos import log
from message import create_content, create_header, create_message

LOGGER = logging.getLogger(name="Lambda")
HEADER = {
    "User-agent": """\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36"""
}
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


def create_response(text: str, messages=None) -> dict:
    if messages is None:
        messages = []
    response = {"text": text, "messages": messages}
    return response


def get_text(item, tag_name: str) -> str:
    """XMLのタグ名を基に文字列を取得.

    タグ名は小文字に置き換えて検索します。
    """
    for elem in item:
        if tag_name in elem.tag.lower():
            return elem.text
    return ""


class CronGroup:
    @staticmethod
    @log(LOGGER)
    async def ait() -> dict:
        """アットマークITの本日の総合ランキングを返します."""
        url = "https://www.atmarkit.co.jp/json/ait/rss_rankindex_all_day.json"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        header = create_header("アットマークITの本日の総合ランキング10件", None)
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
                if item:
                    content = create_content(
                        item["title"].replace(" ", ""), item["link"]
                    )
                    contents.append(content)
            if len(contents) == 0:
                content = create_content("ありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def ait_new_all() -> dict:
        """アットマークITの全フォーラムの新着記事."""
        url = "https://rss.itmedia.co.jp/rss/2.0/ait.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        header = create_header("アットマークITの全フォーラムの新着記事", None)
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
                        content = create_content(
                            get_text(child, "title"), get_text(child, "link")
                        )
                        contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def smart_jp() -> dict:
        """スマートジャパンの新着記事."""
        url = "https://rss.itmedia.co.jp/rss/2.0/smartjapan.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        header = create_header("スマートジャパンの新着記事", None)
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
                        content = create_content(
                            get_text(child, "title"), get_text(child, "link")
                        )
                        contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def itmedia_news() -> dict:
        """ITmedia NEWS 最新記事一覧."""
        url = "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        header = create_header("ITmedia NEWS 最新記事一覧", None)
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
                        content = create_content(
                            get_text(child, "title"), get_text(child, "link")
                        )
                        contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def zdjapan() -> dict:
        """ZDNet Japan 最新情報 総合."""
        url = "http://feeds.japan.zdnet.com/rss/zdnet/all.rdf"
        LOGGER.debug(f"GET {url} header: {HEADER}")
        header = create_header("ZDNet Japan 最新情報 総合", None)
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
                        content = create_content(
                            get_text(child, "title"), get_text(child, "link")
                        )
                        contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def weeklyReport() -> dict:
        """JPCERT から Weekly Report を取得.

        水曜日とかじゃないと何も返ってきません。
        """
        url = "https://www.jpcert.or.jp"
        today = NOW.strftime("%Y-%m-%d")
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            whatsdate = jpcert.select("a.fl")[0].text.replace("号", "")
            if today == whatsdate:
                header = create_header(
                    f"JPCERT の Weekly Report {jpcert.select('a.fl')[0].text}",
                    url + jpcert.select("a.fl")[0].get("href"),
                )
                contents = []
                wkrp = jpcert.select("div.contents")[0].select("li")
                for i, item in enumerate(wkrp, start=1):
                    content = create_content(
                        f"{i}. {item.text}",
                        f"{url}{jpcert.select('a.fl')[0].get('href')}#{i}",
                    )
                    contents.append(content)
                return create_message(header, contents, None)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            header = create_header("JPCERT の Weekly Report", None)
            content = create_content("JPCERTのWeekly Report取得時にエラーが発生しました", None)
            contents = []
            contents.append(content)
            return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def jpcertNotice() -> dict:
        """当日発表の注意喚起を取得.

        何もなきゃ何も言いません。
        """
        url = "https://www.jpcert.or.jp"
        today = NOW.strftime("%Y-%m-%d")
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            items = jpcert.select("div.container")
            header = create_header("JPCERT の直近の注意喚起", None)
            contents = []
            for data in items:
                if data.select("h3") and data.select("h3")[0].text == "注意喚起":
                    for li in data.select("ul.list>li"):
                        published = li.select("a")[0].select("span.left_area")[0].text
                        title = li.select("a")[0].select("span.right_area")[0].text
                        if today in published:
                            link = url + li.select("a")[0].get("href")
                            content = create_content(f"{today} {title}", link)
                            contents.append(content)
                        if YESTERDAY.strftime("%Y-%m-%d") in published:
                            link = url + li.select("a")[0].get("href")
                            content = create_content(
                                f"{YESTERDAY.strftime('%Y-%m-%d')} {title}", link
                            )
                            contents.append(content)
            if len(contents) > 0:
                return create_message(header, contents, None)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            header = create_header("JPCERT の直近の注意喚起", None)
            content = create_content("JPCERTの注意喚起取得時にエラーが発生しました", None)
            contents = []
            contents.append(content)
            return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def jpcertAlert() -> dict:
        """当日発表の脆弱性関連情報を取得.

        何もなきゃ何も言いません。
        """
        url = "https://www.jpcert.or.jp"
        try:
            ret = requests.get(url, headers=HEADER)
            jpcert = BeautifulSoup(ret.content.decode("utf-8"), "html.parser")
            items = jpcert.select("div.container")
            header = create_header("JPCERT の直近の脆弱性関連情報", None)
            contents = []
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
                            content = create_content(title, link)
                            contents.append(content)
            if len(contents) > 0:
                return create_message(header, contents, None)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            header = create_header("JPCERT の直近の注意喚起", None)
            content = create_content("JPCERTの脆弱性関連情報取得時にエラーが発生しました", None)
            contents = []
            contents.append(content)
            return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def techCrunchJapan() -> dict:
        """Tech Crunch Japanのニュースを取得する.

        RSSフィードの情報を取得するので、ちゃんと出来るか不安"""
        header = create_header("Tech Crunch Japan の最新ニュース", None)
        contents = []
        try:
            res = requests.get("https://jp.techcrunch.com/feed/")
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    content = create_content(
                        get_text(child, "title"), get_text(child, "link")
                    )
                    contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)

    @staticmethod
    @log(LOGGER)
    async def uxmilk() -> dict:
        """UX MILKのニュースを取得する."""
        header = create_header("UX MILK の最新ニュース", None)
        contents = []
        try:
            res = requests.get("https://uxmilk.jp/feed")
            root = ET.fromstring(res.content.decode("utf8"))
            for child in root[0]:
                if "item" in child.tag.lower():
                    pub_date = datetime.datetime.strptime(
                        get_text(child, "pubdate")[0:25], "%a, %d %b %Y %H:%M:%S"
                    )
                    if YESTERDAY <= pub_date:
                        content = create_content(
                            get_text(child, "title"), get_text(child, "link")
                        )
                        contents.append(content)
            if len(contents) == 0:
                content = create_content("直近のニュースはありませんでした", None)
                contents.append(content)
        except Exception:
            LOGGER.error(f"{traceback.format_exc()}")
            content = create_content("エラーにより取得できませんでした", None)
            contents.append(content)
        return create_message(header, contents, None)
