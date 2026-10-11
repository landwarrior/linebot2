"""カスタムロガー.

ログ 1 行ごとに通し番号を付け、機密値をマスクする.
番号の置き場所は次の 2 つで、ログ出力時に上から順に使う.

1. Flask のリクエスト処理中は g.unique_key と g.count.
2. それ以外は begin_log_scope() が作ったスコープ. 未呼び出しなら番号は付けない.

変更してよい定数は MASK と SENSITIVE_KEYS だけ.
マスク対象を増やすときは SENSITIVE_KEYS にキー名を小文字で追加する.
置換文字列を変えたいときは MASK を変更する.
ログに現れるキー名は大文字小文字を区別しない. Password も PASSWORD も password もマスクされる.
SENSITIVE_KEYS へ書く文字列は小文字にする. dict の判定が str(key).lower() との完全一致だからである.
判定はキー名の完全一致である. "token" を足しても "my_token" や "user_token" はマスクされない.

ハンドラはプロセス起動時に 1 回だけ付ける. 付ける関数は build_stream_handler().
他のモジュールは同じ名前で getLogger する. ハンドラの追加は繰り返さない.
完成したメッセージに "password": "..." や password=... があれば、値は MASK に置換される.
呼び出し側で json.dumps したり、事前にマスクしたりする必要はない.

ログの形::

    時刻 [レベル](ロガー名)[ユニークキー:通し番号] | メッセージ [in ファイル:行]

ユニークキーは 16 進 7 文字. 通し番号は 1 から始まり、ログのたびに 1 増える.
スコープが無いときは [ユニークキー:通し番号] 自体が出ない.

Flask アプリでの使用例:

    リクエスト中の最初のログで g にキーを作り、以降のログで count を増やす.
    begin_log_scope() は呼ばない. アプリ起動時にハンドラを 1 回付ける.
    before_request 以降、リクエストコンテキストがあるログは同じ番号列になる.
    次のリクエストでは別のキーになり、通し番号は 01 に戻る.
    起動時など、リクエスト外のログには番号は付かない.

        import logging

        from flask import Flask

        from mylogger import build_stream_handler

        app = Flask(__name__)
        logger = logging.getLogger("app")
        logger.setLevel(logging.INFO)
        logger.addHandler(build_stream_handler())

        @app.get("/login")
        def login():
            logger.info("login start")
            logger.info("password=%s", "secret")
            return "ok"

    ビュー以外ではロガーを取るだけにする.

        import logging

        logger = logging.getLogger("app")

        def load_user():
            logger.info("load user")

    同じリクエスト内の出力例::

        2026-10-11 13:32:47,663 [INFO   ](app)[521c64a:01] | login start [in app.py:16]
        2026-10-11 13:32:47,664 [INFO   ](app)[521c64a:02] | password=******** [in app.py:17]
        2026-10-11 13:32:47,665 [INFO   ](app)[521c64a:03] | load user [in users.py:6]

Flask 以外での使用例:

    Lambda やスクリプトには g が無い.
    処理の開始で begin_log_scope() を呼び、unique_key と count の入れ物を作る.
    ハンドラは読み込み時に 1 回だけ付ける. begin_log_scope() は処理のたびに呼ぶ.
    Lambda は実行環境を再利用するので、lambda_handler の先頭で毎回呼ぶと番号が 01 に戻る.
    asyncio のタスクから出しても、同じ通し番号が続く.
    1 プロセスで独立した処理を繰り返すときも、処理の先頭で毎回 begin_log_scope() を呼ぶ.
    呼び忘れたログには番号が付かない.
    Lambda ランタイムはルートロガーにもハンドラを付けている.
    propagate を False にすると、自前ハンドラの 1 行だけが CloudWatch に出る.

        import logging

        from mylogger import begin_log_scope, build_stream_handler

        LOGGER = logging.getLogger("Lambda")
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False
        LOGGER.addHandler(build_stream_handler())

        def lambda_handler(event, context):
            begin_log_scope()
            LOGGER.info("start")
            LOGGER.info("authorization=%s", "Bearer secret")
            return {"statusCode": 200}

    別ファイルからはロガーを取るだけにする.

        import logging

        LOGGER = logging.getLogger("Lambda")

        def push():
            LOGGER.info("push")

    1 回の起動の出力例::

        2026-10-11 13:32:47,663 [INFO   ](Lambda)[521c64a:01] | start [in lambda_function.py:8]
        2026-10-11 13:32:47,664 [INFO   ](Lambda)[521c64a:02] | authorization=******** [in lambda_function.py:9]
        2026-10-11 13:32:47,665 [INFO   ](Lambda)[521c64a:03] | push [in cron.py:5]
"""

import contextvars
import logging
import re
import uuid
from collections.abc import Mapping


# --- 変更してよい定数 ---

# ログに出すときの置換文字列. 元の値の長さは残さない (長さから推測されないようにする).
MASK = "********"

# マスクするキー名. ログ上のキーは大文字小文字を区別しない (Password も password も対象).
# 追加する値は小文字にする. dict の判定が str(key).lower() との完全一致だからである.
# 部分一致ではない. "token" を足しても "my_token" や "user_token" はマスクされない.
# 新しい機密項目をリクエスト JSON / ヘッダ / session に足したら、ここにキー名を追加する.
SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "default_lat",
        "default_lng",
        "hotpepper",
        "webhook_token",
        "webhook_url",
        "authorization",
        "replytoken",
        "token",
        "secret",
    }
)


def _compile_mask_pattern() -> re.Pattern[str]:
    """SENSITIVE_KEYS から文字列マスク用の正規表現を組み立てる.

    内部実装なのでこの関数は変更しない. 対象キーを増やすときは SENSITIVE_KEYS を更新する.
    文字列化されたログの "key": "value" / 'key': 'value' / key=value / Cookie: value を拾う.
    長いキー名を先に置き、csrf_token が token より優先されるようにする.

    Returns:
        コンパイル済みのマスク用正規表現.
    """
    key_alt = "|".join(sorted((re.escape(key) for key in SENSITIVE_KEYS), key=len, reverse=True))
    return re.compile(
        rf"""
        (?P<prefix>
            (?<![A-Za-z0-9_-])
            ['\"]?(?:{key_alt})['\"]?
            \s*[:=]\s*
        )
        (?:
            (?P<quote>['\"])(?P<quoted>.*?)(?P=quote)
            |
            (?P<unquoted>[^,}}]+)
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )


# --- 変更しない定数 (SENSITIVE_KEYS から生成する内部用) ---
_MASK_PATTERN = _compile_mask_pattern()


def _is_sensitive_key(key: object) -> bool:
    """キー名が機密項目かどうかを返す.

    Args:
        key: 判定対象のキー.

    Returns:
        機密キーなら True.
    """
    return str(key).lower() in SENSITIVE_KEYS


def _replace_sensitive(match: re.Match[str]) -> str:
    """正規表現で見つけた機密値を MASK に置換する.

    Args:
        match: 機密キーと値のマッチ結果.

    Returns:
        値をマスクした文字列.
    """
    quote = match.group("quote") or ""
    return f"{match.group('prefix')}{quote}{MASK}{quote}"


def mask_message(message: str) -> str:
    """完成済みログメッセージから機密値をマスクする.

    Args:
        message: ログメッセージ.

    Returns:
        マスク済みメッセージ.
    """
    return _MASK_PATTERN.sub(_replace_sensitive, message)


def _mask_mapping(value: Mapping[object, object]) -> dict[object, object]:
    """マッピングの機密値をマスクした dict を返す.

    Args:
        value: マスク対象のマッピング.

    Returns:
        マスク済みの dict. 元のオブジェクトは変更しない.
    """
    masked: dict[object, object] = {}
    for key, item in value.items():
        if _is_sensitive_key(key):
            masked[key] = MASK
        else:
            masked[key] = mask_sensitive(item)
    return masked


def mask_sensitive(value: object) -> object:
    """機密キーの値をマスクしたコピーを返す.

    dict / list は再帰的に処理する. 文字列はキー名パターンでマスクする.
    元のオブジェクトは変更しない.

    Args:
        value: マスク対象.

    Returns:
        マスク済みの値.
    """
    if isinstance(value, Mapping):
        return _mask_mapping(value)
    if isinstance(value, list):
        return [mask_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(mask_sensitive(item) for item in value)
    if isinstance(value, str):
        return mask_message(value)
    return value


class MaskingFilter(logging.Filter):
    """完成済みログメッセージから機密値をマスクするフィルタ."""

    def filter(self, record: logging.LogRecord) -> bool:
        """ログレコードのメッセージをマスクする.

        Args:
            record: ログレコード.

        Returns:
            常に True. ログ出力は抑制しない.
        """
        record.msg = mask_message(record.getMessage())
        record.args = ()
        return True


class _LogScope:
    """1回のリクエスト、または 1 回の Lambda 起動で共有する通し番号."""

    def __init__(self) -> None:
        """ユニークキーと通し番号の初期値を設定する."""
        self.unique_key = uuid.uuid4().hex[0:7]
        self.count = 1


# asyncio はタスク開始時に ContextVar の参照をコピーする.
# ミュータブルを入れておけば、コピー後も同じオブジェクトの count を更新できる.
_log_scope: contextvars.ContextVar[_LogScope | None] = contextvars.ContextVar("mylogger_scope", default=None)
_flask_available: bool | None = None


def begin_log_scope() -> None:
    """ログのユニークキーと通し番号を初期化する.

    Lambda では lambda_handler の先頭で呼ぶ. 実行環境が再利用されても、呼び出しごとに 1 から始まる.
    Flask ではリクエスト中の g を使うので、この関数は呼ばなくてよい.
    """
    _log_scope.set(_LogScope())


def _flask_request_g() -> object | None:
    """Flask のリクエストコンテキストがあれば g を返す.

    Returns:
        リクエスト中の g. Flask が無い、またはリクエスト外なら None.
    """
    global _flask_available
    if _flask_available is False:
        return None
    try:
        from flask import g, has_request_context
    except Exception:
        _flask_available = False
        return None
    _flask_available = True
    if not has_request_context():
        return None
    return g


def _apply_unique_key(record: logging.LogRecord) -> None:
    """ログレコードへユニークキーを設定し、通し番号を進める.

    Args:
        record: ログレコード.
    """
    g = _flask_request_g()
    if g is not None:
        if not hasattr(g, "count"):
            g.count = 1
        if not hasattr(g, "unique_key"):
            g.unique_key = uuid.uuid4().hex[0:7]
        count = g.count
        record.unique_key = f"[{g.unique_key}:{count:02}]"
        g.count = count + 1
        return
    scope = _log_scope.get()
    if scope is None:
        record.unique_key = ""
        return
    record.unique_key = f"[{scope.unique_key}:{scope.count:02}]"
    scope.count += 1


class UniqueKeyFormatter(logging.Formatter):
    """カスタムログフォーマット."""

    def __init__(self):
        """コンストラクタ."""
        log = "%(asctime)s [%(levelname)-7s](%(name)s)%(unique_key)s | %(message)s [in %(pathname)s:%(lineno)d]"
        super().__init__(log)

    def format(self, record: logging.LogRecord) -> str:
        """ログフォーマットに unique_key を追加して出力できるようにする.

        Args:
            record (logging.LogRecord): ログレコード

        Returns:
            str: ログフォーマット
        """
        _apply_unique_key(record)
        return super().format(record)


def build_stream_handler() -> logging.StreamHandler:
    """マスク Filter と UniqueKeyFormatter を付けた StreamHandler を返す.

    Returns:
        設定済みの StreamHandler.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(UniqueKeyFormatter())
    handler.addFilter(MaskingFilter())
    return handler
