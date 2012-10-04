import urllib2
import urllib
import json

__CLIENT_ID__ = "415200970618.apps.googleusercontent.com"
__CLIENT_SECRET__ = "jpgtxTMwtbQkgWUi1cnSk56f"

__REDIRECT_URI__ = (
                    "urn:ietf:wg:oauth:2.0:oob",
                    #"http://localhost"
                    )

ALL_SCOPES = (
    'https://www.googleapis.com/auth/drive.file ',
    'https://www.googleapis.com/auth/drive ',
    'https://www.googleapis.com/auth/userinfo.email ',
    'https://www.googleapis.com/auth/userinfo.profile'
)


#AUTH_URL = "https://accounts.google.com/o/oauth2/device/code"
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"

def get_authentication():
    params = {}
    params["client_id"] = __CLIENT_ID__
    params["scope"] = " ".join(ALL_SCOPES)
    params["redirect_uri"] = " ".join(__REDIRECT_URI__)
    params["response_type"] = "code"

    url =AUTH_URL + "?"+ urllib.urlencode(params)
    authentication_text = \
"*****************************************************************************\n\
* This is the first time you run the program, in order to be able to use it *\n\
* You have to autorize the application to access to your google drive       *\n\
* information. To do so please got to the following page and copy you code  *\n\
*****************************************************************************\n\
\n\
%s\n\
" % url

    print authentication_text

#Check for the current authentication
def check_authentication():
    import os.path
    PYDRIVE_PATH = os.path.join(os.getenv("HOME"), ".pydrive")
    AUTH_FILE = "auth_config"
    if not os.path.exists(PYDRIVE_PATH):
        print "Creating configuration folder %s" % PYDRIVE_PATH
        os.makedirs(PYDRIVE_PATH)

    if not os.path.exists(os.path.join(PYDRIVE_PATH, AUTH_FILE)):
        get_authentication()
        r = raw_input("Please provide given token\n")
        token = r.strip()
        auth = authenticate_user(token)
        if not auth:
            return None
        with open(os.path.join(PYDRIVE_PATH, AUTH_FILE), "w") as f:
                f.write(json.dumps(auth, indent=2))
    else:
        #TODO read the file
        with open(os.path.join(PYDRIVE_PATH, AUTH_FILE)) as f:
            auth = json.loads("\n".join(f.readlines()))

    return auth

def authenticate_user(token):
    datas = []
    datas.append("code="+token)
    datas.append("client_id="       + __CLIENT_ID__)
    datas.append("client_secret="   + __CLIENT_SECRET__ )
    datas.append("redirect_uri="    + "urn:ietf:wg:oauth:2.0:oob")
    datas.append("grant_type=authorization_code")

    request = urllib2.Request(url=TOKEN_URL,
            data="&".join(datas))

    # Send the request
    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, exc:
        error_content = exc.read()
        print('HTTP status error %s on request (%s)' % (exc.code, error_content))
        return False
    except urllib2.URLError, exc:
        print('Could not reach the server (%s)' % exc.reason)
        return False

    # Read the response
    data = response.read()

    return json.loads(data)


def get_authenticated_http(authentication):
    from oauth2client.client import OAuth2Credentials
    import datetime
    import httplib2
    token_expiry = datetime.datetime.utcnow() + datetime.timedelta(
                seconds=int(result['expires_in']))

    credentials = OAuth2Credentials(result['access_token'], __CLIENT_ID__,
            __CLIENT_SECRET__, result['refresh_token'], token_expiry, TOKEN_URL,
            None, id_token=result['id_token'])


    http = httplib2.Http()
    http = credentials.authorize(http)
    return http


if __name__ == "__main__":

    result = check_authentication()
    http = get_authenticated_http(result)

    from file import File
    f = File(http)
    f.sync("/home/blegrand/temp")



