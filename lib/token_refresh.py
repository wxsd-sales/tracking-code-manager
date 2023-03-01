import json
import traceback

import tornado.gen
import tornado.web

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from lib.settings import Settings

class TokenRefresher(object):
    def __init__(self):
        self._refresh_token = Settings.refresh_token

    def build_access_token_payload(self):
        payload = "grant_type=refresh_token&"
        payload += "client_id={0}&".format(Settings.client_id)
        payload += "client_secret={0}&".format(Settings.client_secret)
        payload += "refresh_token={0}".format(self._refresh_token)
        return payload

    @tornado.gen.coroutine
    def refresh_token(self, state=""):
        print('TokenRefresher.refresh_token called')
        url = "https://webexapis.com/v1/access_token"
        headers = {
            'cache-control': "no-cache",
            'content-type': "application/x-www-form-urlencoded"
            }
        ret_val = None
        payload = self.build_access_token_payload()
        print("refresh token payload:{0}".format(payload))
        try:
            request = HTTPRequest(url, method="POST", headers=headers, body=payload)
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(request)
            resp = json.loads(response.body.decode("utf-8"))
            print("TokenRefresher.refresh_token /access_token Response: {0}".format(resp))
            ret_val = resp["access_token"]
        except Exception as e:
            print("TokenRefresher.refresh_token Exception:{0}".format(e))
            traceback.print_exc()
        raise tornado.gen.Return(ret_val)