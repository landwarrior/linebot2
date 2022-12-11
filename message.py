def create_header(title: str, uri: str) -> dict:
    """メッセージヘッダーを作成する."""
    header = {
        "type": "box",
        "layout": "vertical",
        "contents": [{"type": "text", "text": title, "color": "#e0e0e0", "wrap": True}],
        "backgroundColor": "#35393c",
        "paddingAll": "4px",
    }
    if uri:
        uri = {"action": {"type": "uri", "uri": uri}}
        header.update(uri)
    return header


def create_content(description: str, uri: str) -> dict:
    """メッセージのcontentを作成する."""
    content = {
        "type": "box",
        "layout": "horizontal",
        "paddingAll": "4px",
        "contents": [
            {
                "type": "text",
                "text": description,
                "color": "#35393c",
                "wrap": True,
            }
        ],
        "flex": 0,
    }
    if uri:
        uri = {"action": {"type": "uri", "uri": uri}}
        content.update(uri)
    return content


def create_footer(text: str) -> dict:
    """メッセージのフッターを作成する."""
    footer = {
        "type": "box",
        "contents": [
            {
                "type": "text",
                "text": text,
                "size": "xxs",
                "color": "#4a5054",
                "wrap": True,
            }
        ],
        "paddingAll": "4px",
        "layout": "vertical",
    }
    return footer


def create_message(header: dict, contents: list, footer: dict):
    """メッセージ全体を作成する."""
    message = {
        "type": "flex",
        "altText": "通知",
        "contents": {
            "type": "bubble",
            "size": "giga",
            "header": header,
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "0px",
                "contents": [],
            },
        },
    }
    items = []
    for content in contents:
        if len(items) > 0:
            items.append({"type": "separator"})
        items.append(content)
    message["contents"]["body"]["contents"] = items
    if footer:
        message["contents"]["footer"] = footer
        message["contents"]["styles"] = {"footer": {"separator": True}}
    return message
