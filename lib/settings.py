import os
from dotenv import load_dotenv

load_dotenv()

class Settings(object):
	port = int(os.environ.get("MY_APP_PORT"))
	cookie_secret= os.environ.get("MY_COOKIE_SECRET")

	site_url = os.environ.get("MY_SITE_URL")
	csvfilename = os.environ.get("MY_CSV_FILENAME")
	
	refresh_token = os.environ.get("MY_WEBEX_REFRESH_TOKEN")
	client_id = os.environ.get("MY_WEBEX_CLIENT_ID")
	client_secret = os.environ.get("MY_WEBEX_SECRET")
