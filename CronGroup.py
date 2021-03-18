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
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import requests

LOGGER = logging.getLogger(name="Lambda")
HEADER = {
    'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
}
NOW = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)


def create_response(text, messages=None):
    if messages is None:
        messages = []
    response = {
        'text': text,
        'messages': messages
    }
    return response


class CronGroup:

    @staticmethod
    async def ait() -> None:
        """アットマークITの本日の総合ランキングを返します."""
        LOGGER.info('--START-- ait')
        url = 'https://www.atmarkit.co.jp/json/ait/rss_rankindex_all_day.json'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        res = requests.get(url, headers=HEADER)
        json_str = res.content.decode('sjis').replace(
            'rankingindex(', '').replace(')', '').replace('\'', '"')
        json_data = json.loads(json_str)
        text = '【 アットマークITの本日の総合ランキング10件 】\n'
        messages = []
        for item in json_data['data']:
            if item:
                messages.append({
                    'title': item['title'].replace(' ', ''),
                    'uri': item['link'],
                    'description': item['title'].replace(' ', ''),
                })
            if len(messages) >= 10:
                break
        return create_response(text, messages)
        LOGGER.info('--END-- ait')

    @staticmethod
    async def ait_new_all() -> None:
        """アットマークITの全フォーラムの新着記事."""
        LOGGER.info('--START-- ait_new_all')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        url = 'https://rss.itmedia.co.jp/rss/2.0/ait.xml'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        res = requests.get(url, headers=HEADER)
        root = ET.fromstring(res.content.decode('utf8'))
        text = 'アットマークITの全フォーラムの新着記事'
        messages = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                if child[0].text.startswith('PR:'):
                    continue
                pub_date = datetime.datetime.strptime(child[3].text[0:25], '%a, %d %b %Y %H:%M:%S')
                if yesterday <= pub_date:
                    messages.append({
                        'title': child[0].text,
                        'uri': child[1].text,
                        'description': child[2].text
                    })
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)
        LOGGER.info('--END-- ait_new_all')

    @staticmethod
    async def smart_jp() -> None:
        """スマートジャパンの新着記事."""
        LOGGER.info('--START-- smart_jp')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        url = 'https://rss.itmedia.co.jp/rss/2.0/smartjapan.xml'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        res = requests.get(url, headers=HEADER)
        root = ET.fromstring(res.content.decode('utf8'))
        text = 'スマートジャパンの新着記事'
        messages = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                pub_date = datetime.datetime.strptime(child[3].text[0:25], '%a, %d %b %Y %H:%M:%S')
                if yesterday <= pub_date:
                    messages.append({
                        'title': child[0].text,
                        'uri': child[1].text,
                        'description': child[2].text
                    })
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)
        LOGGER.info('--END-- smart_jp')

    @staticmethod
    async def itmedia_news() -> None:
        """ITmedia NEWS 最新記事一覧."""
        LOGGER.info('--START-- itmedia_news')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        url = 'https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        res = requests.get(url, headers=HEADER)
        root = ET.fromstring(res.content.decode('utf8'))
        text = 'ITmedia NEWS 最新記事一覧'
        messages = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                pub_date = datetime.datetime.strptime(child[3].text[0:25], '%a, %d %b %Y %H:%M:%S')
                if yesterday <= pub_date:
                    messages.append({
                        'title': child[0].text,
                        'uri': child[1].text,
                        'description': child[2].text
                    })
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)
        LOGGER.info('--END-- itmedia_news')

    @staticmethod
    async def zdjapan() -> None:
        """ZDNet Japan 最新情報 総合."""
        LOGGER.info('--START-- zdjapan')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        url = 'http://feeds.japan.zdnet.com/rss/zdnet/all.rdf'
        LOGGER.debug(f"GET {url} header: {HEADER}")
        res = requests.get(url, headers=HEADER)
        root = ET.fromstring(res.content.decode('utf8'))
        text = 'ZDNet Japan 最新情報 総合'
        messages = []
        for child in root:
            if 'item' in child.tag.lower():
                pub_date = datetime.datetime.strptime(child[1].text[0:19], '%Y-%m-%dT%H:%M:%S')
                if yesterday <= pub_date:
                    messages.append({
                        'title': child[3].text,
                        'uri': child[4].text,
                        'description': re.sub(r"<[^>]*?>", '', child[5].text)
                    })
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)
        LOGGER.info('--END-- zdjapan')

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
            return create_response(message, None)

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
            return create_response(notice, None)
        if len(warning_list) > 0:
            warning += '\n'.join(warning_list)
            return create_response(warning, None)

    @staticmethod
    async def techCrunchJapan() -> None:
        """Tech Crunch Japanのニュースを取得する.

        RSSフィードの情報を取得するので、ちゃんと出来るか不安"""
        res = requests.get('https://jp.techcrunch.com/feed/')
        root = ET.fromstring(res.content.decode('utf8'))
        text = "Tech Crunch Japan の最新ニュース"
        messages = []
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
                messages.append(bubble)
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)

    @staticmethod
    async def techRepublicJapan() -> None:
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        yesterday = datetime.datetime.strptime(yesterday.strftime('%Y%m%d'), '%Y%m%d')
        res = requests.get('https://japan.techrepublic.com/rss/latest/')
        root = ET.fromstring(res.content.decode('utf8'))
        text = "TechRepublic Japan の最新ニュース"
        messages = []
        for child in root:
            if 'item' in child.tag.lower():
                date_obj = datetime.datetime.strptime(child[1].text[0:10], '%Y-%m-%d')
                if yesterday <= date_obj:
                    bubble = {
                        'title': child[3].text,
                        'uri': child[4].text,
                        'description': re.sub(r"<[^>]*?>", '', child[5].text)
                    }
                    messages.append(bubble)
        if len(messages) == 0:
            text += '\n直近のニュースはありませんでした'
        return create_response(text, messages)
