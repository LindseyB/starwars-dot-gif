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
from makeGifs import makeGif


config = ConfigParser.ConfigParser()
config.read("config.cfg")
config.sections()
CLIENT_ID = config.get("imgur", "client_id")
API_KEY = config.get("imgur", "api_key")
APP_KEY = config.get("twitter", "app_key")
APP_SECRET = config.get("twitter", "app_secret")
OAUTH_TOKEN = config.get("twitter", "oauth_token")
OAUTH_TOKEN_SECRET = config.get("twitter", "oauth_token_secret")

headers = {"Authorization": "Client-ID " + CLIENT_ID}
url = "https://api.imgur.com/3/upload.json"

while True:
	quote = makeGif(random.randint(4,6), 0, rand=True)
	quote = ' '.join(quote)

	while(os.path.getsize('star_wars.gif') > 2097152):
		subprocess.call(['convert',
						'star_wars.gif',
						'-resize',
						'90%',
						'-coalesce',
						'-layers',
						'optimize',
						'star_wars.gif'])

	try:
		response = requests.post(
			url,
			headers = headers,
			data = {
				'key': API_KEY,
				'image': b64encode(open('star_wars.gif', 'rb').read()),
				'type': 'base64',
				'name': 'star_wars.gif',
				'title': 'Star Wars Dot Gif'
			}
		)
	except requests.exceptions.ConnectionError:
		# try again.
		continue


	try:
		res_json = response.json()
		link = res_json['data']['link']
	except ValueError:
		# try again.
		continue

	twitter = Twython(APP_KEY, APP_SECRET, OAUTH_TOKEN, OAUTH_TOKEN_SECRET)


	status = '"' + quote + '" ' + link + ' #starwarsgif'

	print "tweeting..."
	twitter.update_status(status=status)

	print "sleeping..."
	# sleep 1 hour
	time.sleep(3600)