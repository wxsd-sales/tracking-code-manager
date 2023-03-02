import json
import traceback
import urllib.parse

import tornado.gen
import tornado.web

from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from lib.spark import Spark
from lib.settings import Settings

class WebexOAuthHandler(tornado.web.RequestHandler):

    def build_access_token_payload(self, code, client_id, client_secret, redirect_uri):
        payload = "client_id={0}&".format(client_id)
        payload += "client_secret={0}&".format(client_secret)
        payload += "grant_type=authorization_code&"
        payload += "code={0}&".format(code)
        payload += "redirect_uri={0}".format(redirect_uri)
        return payload

    @tornado.gen.coroutine
    def get_tokens(self, code):
        url = "https://webexapis.com/v1/access_token"
        api_url = 'https://webexapis.com/v1'
        payload = self.build_access_token_payload(code, Settings.client_id, Settings.client_secret, Settings.redirect_uri)
        headers = {
            'cache-control': "no-cache",
            'content-type': "application/x-www-form-urlencoded"
            }
        success = False
        try:
            request = HTTPRequest(url, method="POST", headers=headers, body=payload)
            http_client = AsyncHTTPClient()
            response = yield http_client.fetch(request)
            resp = json.loads(response.body.decode("utf-8"))
            print("****************************************************************************")
            print("WebexOAuthHandler.get_tokens /access_token Response: {0}".format(resp))
            print('----------------------------------------------------------------------------')
            print('refresh token: {0}'.format(resp['refresh_token']))
            print('----------------------------------------------------------------------------')
            person = yield Spark(resp['access_token']).get_with_retries_v2('{0}/people/me'.format(api_url))
            
            print("person.body:{0}".format(person.body))
            print("****************************************************************************")
            success = True
        except Exception as e:
            print("WebexOAuthHandler.get_tokens Exception:{0}".format(e))
            traceback.print_exc()
        raise tornado.gen.Return(success)


    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        response = "Error"
        try:
            if("192.168" not in self.request.full_url()): #this prevents the heartbeat checks from getting pushed through the login the process.
                print('Webex OAuth: {0}'.format(self.request.full_url()))
                if self.get_argument("code", None):
                    code = self.get_argument("code")
                    success = yield self.get_tokens(code)
                    if success:
                        self.redirect("/success")
                    return
                else:
                    authorize_url = '{0}?client_id={1}&response_type=code&redirect_uri={2}&scope={3}'
                    use_url = 'https://webexapis.com/v1/authorize'
                    authorize_url = authorize_url.format(use_url, Settings.client_id, urllib.parse.quote_plus(Settings.redirect_uri), Settings.scopes)
                    print("WebexOAuthHandler.get authorize_url:{0}".format(authorize_url))
                    self.redirect(authorize_url)
                    return
        except Exception as e:
            response = "{0}".format(e)
            print("WebexOAuthHandler.get Exception:{0}".format(e))
            traceback.print_exc()
        self.write(response)
