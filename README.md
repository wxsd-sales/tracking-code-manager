# Tracking Code Manager
Update User Tracking Codes Automatically.  Tracking Codes can be used to track usage amount org users for things like meetings and events, for billing purposes.

## Setup

### Prerequisites & Dependencies: 
python >= v3.8.1

**Python Modules**  
pip install python-dotenv  
pip install tornado==4.5.2

### .env
You will need an environment variables file (.env) with the following declarations:
```
MY_APP_PORT=10031
MY_COOKIE_SECRET="CHANGE_THIS_TO_SOME_SECRET_PHRASE_OR_STRING"

MY_SITE_URL="YOURSITE.webex.com"
MY_CSV_FILENAME="YOUR_FILENAME.csv"

MY_WEBEX_CLIENT_ID="YOUR_WEBEX_INTEGRATION_CLIENT_ID"
MY_WEBEX_SECRET="YOUR_WEBEX_INTEGRATION_CLIENT_SECRET"
MY_WEBEX_REFRESH_TOKEN="YOUR_USER_REFRESH_TOKEN_FOR_THIS_INTEGRATION"
MY_WEBEX_REDIRECT_URI="https://yoursite.domain/reset"

MY_WEBEX_SCOPES=spark%3Akms%20meeting%3Aadmin_preferences_write%20meeting%3Aadmin_preferences_read%20spark%3Apeople_read%20spark-admin%3Apeople_write%20spark-admin%3Aroles_read%20meeting%3Aadmin_config_write%20spark-admin%3Alicenses_read%20meeting%3Aadmin_config_read%20spark-admin%3Apeople_read
```

### Run
```
python server.py
```

## License
All contents are licensed under the MIT license. Please see [license](LICENSE) for details.


## Disclaimer
<!-- Keep the following here -->  
 Everything included is for demo and Proof of Concept purposes only. Use of the site is solely at your own risk. This site may contain links to third party content, which we do not warrant, endorse, or assume liability for. These demos are for Cisco Webex usecases, but are not Official Cisco Webex Branded demos.


## Questions
Please contact the WXSD team at [wxsd@external.cisco.com](mailto:wxsd@external.cisco.com?subject=RepoName) for questions. Or, if you're a Cisco internal employee, reach out to us on the Webex App via our bot (globalexpert@webex.bot). In the "Engagement Type" field, choose the "API/SDK Proof of Concept Integration Development" option to make sure you reach our team. 
