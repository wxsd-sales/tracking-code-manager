
import csv
from inspect import trace
from operator import index, itemgetter
import os
import json
import traceback

import tornado.gen
import tornado.httpserver
import tornado.ioloop
import tornado.web

from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from tornado.options import define, options, parse_command_line
from tornado.httpclient import HTTPError

from lib.oauth import WebexOAuthHandler
from lib.settings import Settings
from lib.spark import Spark
from lib.token_refresh import TokenRefresher

define("debug", default=False, help="run in debug mode")

DOMAIN = 0
RELATIONSHIP = 1
DEPARTMENT = 2

class TrackingDataRequest(object):
    def __init__(self, name, access_token, options=[]):
        self.url = "https://webexapis.com/v1/admin/meeting/config/trackingCodes"
        self.spark = Spark(access_token)
        self.data = {
            "name" : name,
            "siteUrl" : Settings.site_url,
            "options": options,
            "inputMode": "select",
            "hostProfileCode": "notUsed",
            "scheduleStartCodes": [{"service":"All", "type":"optional"}]
        }

    @tornado.gen.coroutine
    def post(self):
        resp = None
        try:
            resp = yield self.spark.post_with_retries(self.url, self.data)
            resp = resp.body
        except HTTPError as he:
            print(he.response)
        raise tornado.gen.Return(resp)

class TaskManager(object):
    def __init__(self, csvfilename):
        self.csvfilename = csvfilename
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.token_refresher = TokenRefresher()
        self.department_index_name = "Department Name"
        self.billing_index_name = "Billing Domain"

    def get_tracking_index_maps_from_csv(self):
        domain_map = []
        department_names = []
        department_index_counter = 0
        with open(self.csvfilename,"r") as f:
            csvreader = csv.reader(f)
            #skip the first row of the CSV file.
            next(csvreader)
            for row in csvreader:
                domain = row[DOMAIN].strip()
                #relationship = row[RELATIONSHIP].strip()
                department = row[DEPARTMENT].strip()
                if department not in department_names:
                    department_names.append(department)
                    department_index_counter += 1
                domain_map.append([domain, department_index_counter - 1])
        return domain_map, department_names

    def get_tracking_index_maps_from_api_results(self, department_options, billing_options):
        department_names = []
        for deparment in department_options:
            department_names.append(deparment["value"])
        
        domain_map = {}
        for domain_option in billing_options:
            domain, index = domain_option["value"].rsplit("-",1)
            try:
                domain_map.update({domain:int(index)})
            except Exception as ex:
                print("Error with domain: {0}, index:{1}".format(domain, index))
                traceback.print_exc()
        return domain_map, department_names


    @tornado.gen.coroutine
    def get_api_tracking_indexes(self, access_token):
        url = "https://webexapis.com/v1/admin/meeting/config/trackingCodes"
        spark = Spark(access_token)
        resp = yield spark.get_with_retries_v2(url)
        items = resp.body.get('items')
        counter = len(items)
        print("Tracking Codes Found:{0}".format(counter))
        department_index = None
        billing_index = None
        for item in items:
            index_name = item.get("name")
            if index_name == self.department_index_name:
                department_index = item
            elif index_name == self.billing_index_name:
                billing_index = item
        raise tornado.gen.Return([department_index, billing_index])

    @tornado.gen.coroutine
    def create_department_tracking_index(self, access_token, department_names):
        tdr = TrackingDataRequest(self.department_index_name, access_token)
        for department in department_names:
            tdr.data["options"].append({"value":department, "defaultValue":False})
        ret_val = yield tdr.post()
        return ret_val
    
    @tornado.gen.coroutine
    def create_billing_tracking_index(self, access_token, domain_map):
        tdr = TrackingDataRequest(self.billing_index_name, access_token, [])
        for domain in domain_map:
            tdr.data["options"].append({"value":"{0}-{1}".format(domain[0], domain[1]), "defaultValue":False})
        print(tdr.data["options"])
        print("Length of Billing Index Options: {0}".format(len(tdr.data["options"])))
        ret_val = yield tdr.post()
        return ret_val
        
    
    @tornado.gen.coroutine
    def update_people(self, access_token, domain_map, department_names):
        try:
            url = "https://webexapis.com/v1/people?max=100"
            spark = Spark(access_token)
            counter = 0
            while url != None:
                #print('get people url:{0}'.format(url))
                people_resp = yield spark.get_with_retries_v2(url)
                items = people_resp.body.get('items')
                counter += len(items)
                print("people found:{0}".format(counter))
                for person in items:
                    try:
                        email = person.get("emails")[0]
                        id = person.get("id")
                        username, domain = email.split("@")
                        print("domain {0}, user: {1}".format(domain, email))
                        if domain in domain_map:
                            try:
                                user_department_index =  domain_map[domain]
                                resp = yield spark.get_with_retries_v2("https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes?personId={0}".format(id))
                                oldTrackingCodes = resp.body.get("trackingCodes", [])
                                print("siteUrl:{0}, old trackingCodes:{1}".format(resp.body.get("siteUrl"), oldTrackingCodes))
                                
                                billing_code_value = "{0}-{1}".format(domain, user_department_index)
                                department_code_value = department_names[user_department_index]

                                saveTrackingCodes = []
                                existing_codes = 0
                                for trackingCode in oldTrackingCodes:
                                    if trackingCode["name"] not in [self.billing_index_name, self.department_index_name] :
                                        saveTrackingCodes.append(trackingCode)
                                    elif trackingCode["name"] == self.billing_index_name and trackingCode["value"] == billing_code_value:
                                        existing_codes += 1
                                    elif trackingCode["name"] == self.department_index_name and trackingCode["value"] == department_code_value:
                                        existing_codes += 1
                                if existing_codes < 2:
                                    newTrackingCodes = [{
                                        "name":self.billing_index_name,
                                        "value": billing_code_value
                                    },{
                                        "name":self.department_index_name,
                                        "value": department_code_value
                                    }]
                                    newTrackingCodes += saveTrackingCodes
                                    print("new trackingCodes:{0}".format(newTrackingCodes))
                                    data = {
                                        "siteUrl": Settings.site_url,
                                        "personId": id,
                                        "trackingCodes": newTrackingCodes
                                    }
                                    resp = yield spark.post_with_retries("https://webexapis.com/v1/admin/meeting/userconfig/trackingCodes", data, method="PUT")
                                else:
                                    print("User already has latest tracking codes.")
                            except HTTPError as he:
                                print(he.response)
                        else:
                            print("domain {0} not in code_map, skipping tracking code update for this user: {1}".format(domain, email))
                    except Exception as ex:
                        traceback.print_exc()
                url = people_resp.headers.get("Link")
                if url:
                    parts = url.split(">")
                    url = parts[0][1:]
                    print("next people url:{}".format(url))
        except Exception as e:
            traceback.print_exc()
        #raise tornado.gen.Return()

    @tornado.gen.coroutine
    def run_loop(self):
        while True:
            print("TaskManager.run_loop - running")
            try:
                #1. Retrieve Tracking Codes from CSV
                domain_map, department_names = self.get_tracking_index_maps_from_csv()
                print("Number of CSV Rows:{0}".format(len(domain_map)))
                #2. Generate an access_token from our refresh token
                access_token = yield self.token_refresher.refresh_token()
                #3. Create a map of tracking codes from API too
                department_index, billing_index = yield self.get_api_tracking_indexes(access_token)
                #4. create any missing tracking codes using the API that exist in CSV but not in the API
                if department_index == None:
                    print("No {0} Tracking Index, creating...".format(self.department_index_name))
                    department_index = yield self.create_department_tracking_index(access_token, department_names)
                    print("Created {0} Tracking Index.".format(self.department_index_name))
                else:
                    print("{0} Tracking Index Already Exists.".format(self.department_index_name))
                if billing_index == None:
                    print("No {0} Tracking Index, creating...".format(self.billing_index_name))
                    billing_index = yield self.create_billing_tracking_index(access_token, domain_map)
                    print("Created {0} Tracking Index.".format(self.billing_index_name))
                else:
                    print("{0} Tracking Index Already Exists.".format(self.billing_index_name))
                print(department_index["name"])
                print(billing_index["name"])
                
                domain_map, department_names = self.get_tracking_index_maps_from_api_results(department_index["options"], billing_index["options"])
                yield self.update_people(access_token, domain_map, department_names)
                
                now = datetime.utcnow()
                print("TaskManager.run_loop - utc now:{0}".format(now))
                next_run = now + timedelta(days=1)
                next_run = next_run.replace(hour=7, minute=0, second=0, microsecond=0)
                print("TaskManager.run_loop - next_run:{0}".format(next_run))
                next_run_seconds = (next_run - now).seconds
            except Exception as e:
                traceback.print_exc()
            print("TaskManager.run_loop - done. Sleeping for {0} seconds.".format(next_run_seconds))
            yield tornado.gen.sleep(next_run_seconds)

class AuthFailedHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            print("AuthFailedHandler GET")
            self.render("auth-failed.html")
        except Exception as e:
            traceback.print_exc()

class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        try:
            print("MainHandler GET")
            self.render("index.html")
        except Exception as e:
            traceback.print_exc()


@tornado.gen.coroutine
def main():
    try:
        parse_command_line()
        app = tornado.web.Application([
                (r"/success", MainHandler),
                (r"/reset", WebexOAuthHandler),
                (r"/authentication-failed", AuthFailedHandler),
              ],
            template_path=os.path.join(os.path.dirname(__file__), "html_templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret=Settings.cookie_secret,
            xsrf_cookies=False,
            debug=options.debug,
            )
        task_manager = TaskManager(Settings.csvfilename)
        app.settings['task_manager'] = task_manager
        server = tornado.httpserver.HTTPServer(app)
        server.bind(Settings.port)
        print("main - Serving... on port {0}".format(Settings.port))
        server.start()
        tornado.ioloop.IOLoop.instance().spawn_callback(task_manager.run_loop)
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    main()
