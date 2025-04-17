import logging
import aiohttp
import json
import hmac
import hashlib
import base64
import time
import urllib.parse

_LOGGER = logging.getLogger(__name__)

class DingTalkNotify:
    """Class for interacting with DingTalk Notify API."""

    def __init__(self, token, secret=None):
        """Initialize the DingTalk Notify API."""
        self.token = token
        self.secret = secret
        self.url = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}"

    def _get_sign(self):
        """Get signed URL."""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f"{timestamp}\n{self.secret}"
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    async def send_message(self, **kwargs):
        """Send a message via DingTalk Notify."""
        # 初始化通用参数
        headers = {"Content-Type": "application/json;charset=utf-8"}

        # 消息体已经由 __init__.py 构造好，直接使用 kwargs
        data_info = kwargs

        # 生成签名并拼接 URL
        if self.secret:
            timestamp, sign = self._get_sign()
            self.url = f"https://oapi.dingtalk.com/robot/send?access_token={self.token}&timestamp={timestamp}&sign={sign}"

        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, data=json.dumps(data_info), headers=headers) as response:
                    response_data = await response.json()
                    if response_data.get("errmsg") != "ok":
                        _LOGGER.error(f"消息发送失败：{response_data}")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"网络请求失败：{e}")
        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON 解析失败：{e}")