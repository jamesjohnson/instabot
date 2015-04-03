from flask import Flask
app = Flask(__name__)

import random
import requests
from instagram.client import InstagramAPI
from models import Session, ScrapeRequest, User

CODE = ""

"""
curl \-F 'client_id=' \
    -F 'client_secret=' \
    -F 'grant_type=authorization_code' \
    -F 'redirect_uri=http://localhost/instagram' \
    -F 'code=' \https://api.instagram.com/oauth/access_token
"""


import hmac
from hashlib import sha256

ips = ''
secret = ''

signature = hmac.new(secret, ips, sha256).hexdigest()
header = '|'.join([ips, signature])

access_token = ""
api = InstagramAPI(access_token=access_token)
count = 0
while True:
    session = Session()
    profile = ScrapeRequest.get_unliked_request(session)
    profile.liked = True
    try:
        user = api.user_search(q=profile.url)[0]
        recent_media, next_ = api.user_recent_media(user_id=user.id, count=20)
        for photo in recent_media[:3]:
            response = requests.post("https://api.instagram.com/v1/media/{0}/likes".format(photo.id),
                params={"access_token": access_token},
                headers={"X-Insta-Forwarded-For":header})
            count += 1
            print photo
    except Exception, e:
        print e
        pass
    session.commit()
    if count > 50:
        break
