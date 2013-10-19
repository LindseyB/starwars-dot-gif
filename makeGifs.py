#!/usr/bin/python

from images2gif import writeGif
from PIL import Image, ImageFont, ImageDraw
from numpy import array
import os
import re
import ConfigParser
import pysrt
import random

sub_files = {   4: 'subs/IV-A.New.Hope[1977]DvDrip-aXXo.srt',
                5: 'subs/V-The.Empire.Strikes.Back[1980]DvDrip-aXXo.srt',
                6: 'subs/VI-Return.Of.The.Jedi[1983]DvDrip-aXXo.srt' }

def striptags(data):
	# I'm a bad person, don't ever do this.
	# Only okay, because of how basic the tags are.
	p = re.compile(r'<.*?>')
	return p.sub('', data)

def drawText(draw, x, y, text, font):
	# black outline
	draw.text((x-1, y),text,(0,0,0),font=font)
	draw.text((x+1, y),text,(0,0,0),font=font)
	draw.text((x, y-1),text,(0,0,0),font=font)
	draw.text((x, y+1),text,(0,0,0),font=font)

	# white text
	draw.text((x, y),text,(255,255,255),font=font)

def makeGif(source, sub_index, rand=False, no_quote=False, custom_subtitle=""):
	config = ConfigParser.ConfigParser()
	config.read("config.cfg")

	config.sections()

	vlc_path = config.get("general", "vlc_path")

	video_path = config.get("general", "ep"+str(source)+"_path")
	screencap_path = os.path.join(os.path.dirname(__file__), "screencaps")

	# delete the contents of the screencap path
	file_list = os.listdir(screencap_path)
	for file_name in file_list:
		os.remove(os.path.join(screencap_path, file_name))

	# read in the quotes for the selected movie
	subs = pysrt.open(sub_files[source])

	if rand:
		sub_index = random.randint(0, len(subs)-1)

	if no_quote:
		start = (3600 * subs[sub_index].end.hours) + (60 * subs[sub_index].end.minutes) + subs[sub_index].end.seconds + (0.001*subs[sub_index].end.milliseconds)
		end = (3600 * subs[sub_index+1].start.hours) + (60 * subs[sub_index+1].start.minutes) + subs[sub_index+1].start.seconds + (0.001*subs[sub_index+1].start.milliseconds)
	else:
		start = (3600 * subs[sub_index].start.hours) + (60 * subs[sub_index].start.minutes) + subs[sub_index].start.seconds + (0.001*subs[sub_index].start.milliseconds)
		end = (3600 * subs[sub_index].end.hours) + (60 * subs[sub_index].end.minutes) + subs[sub_index].end.seconds + (0.001*subs[sub_index].end.milliseconds)
		text = striptags(subs[sub_index].text).split("\n")

	if len(custom_subtitle) > 0:
		text = [custom_subtitle]

	# tell vlc to go get images for gifs
	cmd = '"{0}" -Idummy --video-filter scene -V dummy --no-audio --scene-height=256 --scene-width=512 --scene-format=png --scene-ratio=1 --start-time={3} --stop-time={4}  --scene-prefix=thumb --scene-path="{1}"  "{2}" vlc://quit'.format(vlc_path, screencap_path, video_path, start, end)
	os.popen(cmd)

	file_names = sorted((fn for fn in os.listdir(screencap_path)))
	images = []

	font = ImageFont.truetype("fonts/DejaVuSansCondensed-BoldOblique.ttf", 16)

	# remove the first image from the list
	file_names.pop(0)

	for f in file_names:
		try:
			image = Image.open(os.path.join(screencap_path,f))
			draw = ImageDraw.Draw(image)

			try:
  				image_size
			except NameError:
				image_size = image.size

			# deal with multi-line quotes
			try:
				if len(text) == 2:
					# at most 2?
					text_size = font.getsize(text[0])
					x = (image_size[0]/2) - (text_size[0]/2)
					y = image_size[1] - (2*text_size[1]) - 5 # padding
					drawText(draw, x, y, text[0], font)

					text_size = font.getsize(text[1])
					x = (image_size[0]/2) - (text_size[0]/2)
					y += text_size[1]
					drawText(draw, x, y, text[1], font)
				else:
					text_size = font.getsize(text[0])
					x = (image_size[0]/2) - (text_size[0]/2)
					y = image_size[1] - text_size[1] - 5 # padding
					drawText(draw, x, y, text[0], font)
			except NameError:
				pass
				# do nothing.

			# if not all black?
			if image.getbbox():
				# add it to the array
				images.append(array(image))
				print 'image appended.'
			else:
				print 'all black frame found.'
		except IOError:
			print 'empty frame found.'

	filename = "star_wars.gif"


	# create a fuckin' gif
	print "generating gif..."
	writeGif(filename, images, nq=10, dither=True)

	if rand:
		try:
			return text
		except:
			return []


if __name__ == '__main__':
	# by default we create a random gif
	makeGif(random.randint(4,6), 0, rand=True, no_quote=bool(random.getrandbits(1)))

