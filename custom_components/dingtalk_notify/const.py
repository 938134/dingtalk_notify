"""Constants for DingTalk Notify."""
DOMAIN = "dingtalk_notify"
CONF_TOKEN = "token"
CONF_SECRET = "secret"

MSG_TEXT = "text"
MSG_MARKDOWN = "markdown"
MSG_LINK = "link"
MSG_ACTIONCARD = "actionCard"
OPTION_MSG_TYPES = [MSG_TEXT, MSG_MARKDOWN, MSG_LINK, MSG_ACTIONCARD]

DEFAULT_TIMEOUT = 10
RETRY_TIMES = 3

MANUFACTURER = "钉钉消息机器人"
MODEL = "dingtalk"

def short_token(token: str) -> str:
    return token[-4:] if len(token) >= 4 else token

MSG_TYPE_NAME = {
    MSG_TEXT: "文本",
    MSG_MARKDOWN: "Markdown",
    MSG_LINK: "链接",
    MSG_ACTIONCARD: "互动卡片",
}