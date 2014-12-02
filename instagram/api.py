import random
import requests
from instagram.client import InstagramAPI
from models import Session, ScrapeRequest

import dj_database_url

CODE = "fd9c0acc616f41c4801eed3fa7c7ca14"

"""
curl \-F 'client_id=393749080807444a975e11c6060a58be' \
    -F 'client_secret=95775738376b4cb58b2b69e30492cd91' \
    -F 'grant_type=authorization_code' \
    -F 'redirect_uri=http://localhost/instagram' \
    -F 'code=fd9c0acc616f41c4801eed3fa7c7ca14' \https://api.instagram.com/oauth/access_token
"""

DATABASES['default'] =  dj_database_url.config()

import hmac
from hashlib import sha256

ips = '72.69.141.254'
secret = '6dc1787668c64c939929c17683d7cb74'

signature = hmac.new(secret, ips, sha256).hexdigest()
header = '|'.join([ips, signature])

access_token = "6767180.3937490.c6dfa67eb594468aa4aa9fe6cd2539a0"
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
