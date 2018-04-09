import base64
import json
import requests
import ConfigParser
import random
import os
import time
import subprocess

from twython import Twython
from base64 import b64encode
from makeGifs import makeGif, check_config


config = ConfigParser.ConfigParser()
config.read("config.cfg")
config.sections()
slugs = check_config("config.cfg")[3]

CLIENT_ID = config.get("imgur", "client_id")
API_KEY = config.get("imgur", "api_key")
APP_KEY = config.get("twitter", "app_key")
APP_SECRET = config.get("twitter", "app_secret")
OAUTH_TOKEN = config.get("twitter", "oauth_token")
OAUTH_TOKEN_SECRET = config.get("twitter", "oauth_token_secret")

headers = {"Authorization": "Client-ID " + CLIENT_ID}
url = "https://api.imgur.com/3/upload.json"

while True:
    while True:
        try:
            # you can set many more options, check the makeGif-function
            quote = makeGif(random.choice(slugs))
            quote = ' '.join(quote)
        except:
            print('something went wrong during gif-generation')
            continue
        else:
            break

    # first pass reduce the amount of colors
    if(os.path.getsize('star_wars.gif') > 5242880):
        subprocess.call(['convert',
                         'star_wars.gif',
                         '-layers',
                         'optimize',
                         '-colors',
                         '128',
                         '-loop',
                         '0',
                         'star_wars.gif'])

    # second pass reduce the amount of colors
    if(os.path.getsize('star_wars.gif') > 5242880):
        subprocess.call(['convert',
                         'star_wars.gif',
                         '-layers',
                         'optimize',
                         '-colors',
                         '64',
                         '-loop',
                         '0',
                         'star_wars.gif'])

    # other passes reduce the size
    while(os.path.getsize('star_wars.gif') > 5242880):
        subprocess.call(['convert',
                         'star_wars.gif',
                         '-resize',
                         '90%',
                         '-coalesce',
                         '-layers',
                         'optimize',
                         '-loop',
                         '0',
                         'star_wars.gif'])

    try:
        response = requests.post(
            url,
            headers=headers,
            data={
                'key': API_KEY,
                'image': b64encode(open('star_wars.gif', 'rb').read()),
                'type': 'base64',
                'name': 'star_wars.gif',
                'title': 'Star Wars Dot Gif'
            }
        )
    except (requests.exceptions.ConnectionError, OpenSSL.SSL.SysCallError):
        # try again.
        continue

    try:
        res_json = response.json()
        link = res_json['data']['link']
    except (KeyError, ValueError):
        # try again.
        continue

    twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)

    # upload media
    gif = open('star_wars.gif', 'rb')
    response = twitter.upload_media(media=gif)

    if len(quote) > 70:
        quote = (quote[:67] + '...')

    if len(quote) == 0:
        quote = "..."

    status = '"' + quote + '" ' + link + ' #starwarsgif'

    print "tweeting..."
    try:
        twitter.update_status(status=status, media_ids=[response['media_id']])
    except:
        # error with twitter sleep a bit and try again
        time.sleep(1800)
        continue

    print "sleeping..."
    # sleep 1 hour
    time.sleep(3600)
