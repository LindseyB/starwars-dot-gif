#!env python

import ast
import argparse
import imageio
import random
import re
import os
import pysrt
import subprocess
import configparser
from numpy import array
from PIL import Image, ImageFont, ImageDraw

# defaults

CONFIG_FILE = "config.cfg"
PALLETSIZE = 256  # number of colors used in the gif, rounded to a power of two
WIDTH = 512  # of the exports/gif, aspect ratio 2.35:1
HEIGHT = 220  # of the exports/gif, aspect ratio 2.35:1
FRAME_DURATION = 0.1  # how long a frame/image is displayed
PADDING = [0]  # seconds to widen the capture-window
DITHER = 2  # only every <dither> image will be used to generate the gif
FRAMES = 0  # how many frames to export, 0 means as many as are available
SCREENCAP_PATH = os.path.join(os.path.dirname(__file__), "screencaps")
FONT_PATH = "fonts/DejaVuSansCondensed-BoldOblique.ttf"
FONT_SIZE = 16


def check_config(config_file):
    if not os.path.exists(config_file):
        print('Config file not found: {}'.format(config_file))
        exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)
    config.sections()

    try:
        ffmpeg_path = config.get("general", "ffmpeg_path")
        vlc_path = config.get("general", "vlc_path")
        movies = [movie_sanity_check(m) for m in ast.literal_eval(
            config.get('general', 'videos')) if movie_sanity_check(m)]
    except configparser.NoOptionError as ex:
        print('Option missing from config-file: {}'.format(ex.message))
        exit(1)
    except SyntaxError as err:
        items = err[1]
        print('{}: {} on line {}, character {} in {}'.format(
            err[0].capitalize(), items[0], items[1], items[2], config_file))
        print('This might be wrong syntax in the videos-setting')
        exit(1)
    slugs = [movie['slug'] for movie in movies]

    if not movies:
        print('Your config does not contain any valid movies')
        exit(1)

    return (ffmpeg_path, vlc_path, movies, slugs)


def movie_sanity_check(movie):
    # see if video_path is set
    if 'movie_path' not in movie or not os.path.exists(movie['movie_path']):
        print('Movie \'{}\' has no readable video_path set'.format(
            movie['title'] if 'title' in movie else 'unknown'))
        return False

    if 'subtitle_path' not in movie or not os.path.exists(
            movie['subtitle_path']):
        candidate = movie['movie_path'][:-3] + "srt"
        if os.path.exists(candidate):
            movie['subtitle_path'] = candidate
            return movie

        candidate = movie['movie_path'][:-3] + "eng.srt"
        if os.path.exists(candidate):
            movie['subtitle_path'] = candidate
            return movie
        return False

    return movie


def get_movie_by_slug(slug, movies):
    for movie in movies:
        if movie['slug'] == slug:
            return movie
    print('movie with slug "{}" not found in config.'.format(slug))
    exit(1)


def striptags(data):
    #  I'm a bad person, don't ever do this.
    #  Only okay, because of how basic the tags are.
    p = re.compile(r'<.*?>')
    return p.sub('', data)


def drawText(draw, x, y, text, font):
    """Draws a white text with a black outline.

    Arguments:
        draw {PIL.Image} -- The image to draw in
        x {int} -- x-coordinate to start drawing in
        y {int} -- y-coordinate to start drawing in
        text {str} -- Text to render (please verify font-sizing)
        font {ImageFont.Font} -- Font to render text in
    """

    #  black outline
    draw.text((x-1, y), text, (0, 0, 0), font=font)
    draw.text((x+1, y), text, (0, 0, 0), font=font)
    draw.text((x, y-1), text, (0, 0, 0), font=font)
    draw.text((x, y+1), text, (0, 0, 0), font=font)

    #  white text
    draw.text((x, y), text, (255, 255, 255), font=font)


def makeGif(movie_slug, sub_index=[-1], custom_subtitle=[""], quote=True,
            frames=0, filename="star_wars.gif", dither=DITHER,
            padding=PADDING, palletsize=PALLETSIZE, width=WIDTH, height=HEIGHT,
            frame_duration=FRAME_DURATION, font_path=FONT_PATH,
            font_size=FONT_SIZE):
    """
    This function relies on some global variables that need to be set
    before you can run the function.
    Namely: movies, ffmpeg_path, vlc_path.

    This function will the pull frames for the selected movie and render
    subtitles over them to

    Arguments:
        movie_slug {[str]} -- Select the movie(s) to pull a gif from, this must
                              be defined in the config-file.

    Keyword Arguments:
        sub_index [{int}] -- List of indexes of the subtitle "lines" to use
                             (default: {[-1]})
        custom_subtitle [{str}] -- Replace the selected quote with your own
                                   text (default: {[""]})
        quote {bool} -- False will export the time-slot between the selected
                        index and next index in the subtitle file.
                        True exports the timespan given by the index
                        (default: {True})
        frames {int} -- Only export <frames> images to the gif (default: {0})
        filename {str} -- Name to safe the gif under
                          (default: {"star_wars.gif"})
        dither {int} -- Every <dither> image is used in the gif (2 means every
                        second exported image is used) (default: {2})
        padding {[int]} -- Seconds to add at the end and beginning of the gif
                           (default: {[0]})
        palletsize {int} -- Palletsize, will be rounded to the nearest power
                            of two (default: {256})
        width {int} -- Width of the gif to generate (height does not scale to
                       ratio!) (default: {512})
        height {int} -- Height of the gif to generate (width does not scale to
                       ratio!) (default: {256})
        frame_duration {float} -- Seconds each frame will be shown in the gif.
                                  (default: {0.1})
        font_path {str} -- Font to render the subtitle in (default:
                           {'fonts/DejaVuSansCondensed-BoldOblique.ttf'})
        font_size {str} -- Font-size to render in (important of you change the
                           width/height of the gif) (default: {16})

        Raises:
            Exception -- If a required file is not found

        Returns:
            [str] -- The quoted text you selected or input.

    """

    # if this function is not called via commandline we need to parse movies
    (ffmpeg_path, vlc_path, movies, slugs) = check_config(CONFIG_FILE)

    movie = get_movie_by_slug(movie_slug, movies)
    # make sure movie is present
    if not os.path.exists(movie['movie_path']):
        raise Exception('Movie not found.')

    # make sure subtitles are present
    if not os.path.exists(movie['subtitle_path']):
        raise Exception('Subtitles not found.')

    # cleanup from previous runs (if any)
    if not os.path.exists(SCREENCAP_PATH):
        os.makedirs(SCREENCAP_PATH)

    # these are the frames that will be exported
    images = []
    meta = []

    # read in the quotes for the selected movie
    subs = pysrt.open(movie['subtitle_path'])
    font = ImageFont.truetype(font_path, font_size)

    loop = 0
    for working_index in sub_index:
        # delete the contents of the screencap path
        file_list = os.listdir(SCREENCAP_PATH)
        for file_name in file_list:
            os.remove(os.path.join(SCREENCAP_PATH, file_name))

        # see of we have custom quotes
        if len(custom_subtitle) > loop:
            working_subtitle = custom_subtitle[loop]
        else:
            working_subtitle = ""

        # get padding from array
        if isinstance(padding, (int, float)):
            padding_left = padding
            padding_right = padding
        elif len(padding) == 2:
            padding_left = padding[0]
            padding_right = padding[1]
        elif len(padding) >= (2 * loop + 2):
            padding_left = padding[2 * loop]
            padding_right = padding[2 * loop + 1]
        elif len(padding) >= (2 * loop + 1):
            padding_left = padding[2 * loop]
            padding_right = padding[2 * loop]
        else:
            # this should not happen
            padding_left = 0
            padding_right = 0

        # if no quote selected, set a random one
        if working_index < 1:
            working_index = random.randint(1, len(subs))
        if working_index > len(subs)+1:
            print('subtitle index not available')
            exit(1)

        subtitle = subs[working_index-1]
        next_subtitle = subs[working_index]

        # setting text to "subtitle" with
        if len(working_subtitle) > 0:
            text = [working_subtitle]
        else:
            text = striptags(subtitle.text).split("\n")

        print('generating images from video ...')

        # Both ffmpeg and vlc write a lot of stuff to stdout, supressing
        FNULL = open(os.devnull, 'w')

        if ffmpeg_path:
            print('using ffmpeg.')
            # ffmpeg
            # getting timespans (begin and duration)
            if quote:
                start = subtitle.start - pysrt.SubRipTime(
                    0, 0, padding_left)
                diff = subtitle.end - subtitle.start
            else:
                start = subtitle.end - pysrt.SubRipTime(
                    0, 0, padding_left)
                diff = next_subtitle.start - subtitle.end

            duration = str(diff.seconds +
                        (diff.milliseconds*0.001) +
                        padding_right)
            start = str(start).replace(',', '.')

            # calling ffmpeg (or whatever binary talks in ffmpeg-options)
            subprocess.call([
                ffmpeg_path,
                '-ss',
                start,
                '-i',
                movie['movie_path'],
                '-t',
                duration,
                '-s',
                '{}x{}'.format(width, height),
                SCREENCAP_PATH + '/thumb%05d.png'],
                stdout=FNULL, stderr=subprocess.STDOUT)
        else:
            # vlc
            print('using vlc')
            # getting timespans
            if quote:
                start = ((3600 * subtitle.start.hours) +
                        (60 * subtitle.start.minutes) +
                        subtitle.start.seconds -
                        padding_left +
                        (0.001*subtitle.start.milliseconds))
                end = ((3600 * subtitle.end.hours) +
                    (60 * subtitle.end.minutes) +
                    subtitle.end.seconds +
                    padding_right +
                    (0.001*subtitle.end.milliseconds))
            else:
                start = ((3600 * subtitle.end.hours) +
                        (60 * subtitle.end.minutes) +
                        subtitle.end.seconds +
                        (0.001*subtitle.end.milliseconds))
                end = ((3600 * next_subtitle.start.hours) +
                    (60 * next_subtitle.start.minutes) +
                    next_subtitle.start.seconds +
                    (0.001*next_subtitle.start.milliseconds))
            # calling vlc
            subprocess.call([
                vlc_path,
                '-Idummy',
                '--video-filter',
                'scene',
                '-Vdummy',
                '--no-audio',
                '--scene-height=256',
                '--scene-width=512',
                '--scene-format=png',
                '--scene-ratio=1',
                '--start-time='+str(start),
                '--stop-time='+str(end),
                '--scene-prefix=thumb',
                '--scene-path='+SCREENCAP_PATH,
                movie['movie_path'],
                'vlc://quit'
            ], stdout=FNULL, stderr=subprocess.STDOUT)

        # Generating images done
        file_names = sorted((fn for fn in os.listdir(SCREENCAP_PATH)))
        if not file_names:
            print('no images generated, aborting.')
            return
        print('generated {} images.'.format(len(file_names)))

        for f in file_names[::dither]:
            try:
                image = Image.open(os.path.join(SCREENCAP_PATH, f))
                draw = ImageDraw.Draw(image)
                image_size = image.size

                # deal with multi-line quotes
                try:
                    if len(text) == 2:
                        # at most 2?
                        text_size = font.getsize(text[0])
                        x = (image_size[0]/2) - (text_size[0]/2)
                        y = image_size[1] - (2*text_size[1]) - 8  # padding
                        drawText(draw, x, y, text[0], font)

                        text_size = font.getsize(text[1])
                        x = (image_size[0]/2) - (text_size[0]/2)
                        y += text_size[1]
                        drawText(draw, x, y, text[1], font)
                    else:
                        text_size = font.getsize(text[0])
                        x = (image_size[0]/2) - (text_size[0]/2)
                        y = image_size[1] - text_size[1] - 8  # padding
                        drawText(draw, x, y, text[0], font)
                except NameError:
                    pass
                # do nothing.

                # if not all black?
                if image.getbbox():
                    # add it to the array
                    images.append(array(image))
                    if frames != 0 and len(images) == frames:
                        # got all the frames we need - all done
                        break
                else:
                    print('all black frame found.')
            except IOError:
                print('empty frame found.')
        meta.append('{}: "{}" (index {}, {})'.format(
            movie['title'], '\n'.join(text), working_index, subtitle.start))
        # this is so we can have multiple quotes and paddings and stuff
        loop += 1

    # create a fuckin' gif
    print('selected {} images.'.format(len(images)))
    print('generating gif...')
    imageio.mimsave(filename,
                    images,
                    palettesize=palletsize,
                    duration=frame_duration,
                    subrectangles=False)
    print('generated gif.')
    print('Used:\n{}'.format('\n'.join(meta)))
    print('done.')
    return text


if __name__ == '__main__':
    # read config (we need this for default-generation below)
    (ffmpeg_path, vlc_path, movies, slugs) = check_config(CONFIG_FILE)

    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--movie', type=str, metavar="MOVIE", nargs='*',
        default=slugs,
        help=('movie slug, space-separated (default: {})'.format(
            ' '.join(slugs)
        )))

    parser.add_argument(
        '--index', dest='index', type=int, nargs='*', default=[-1],
        help='subtitle index (starts at 1)')

    parser.add_argument(
        '--subtitle', dest='subtitle', type=str, nargs='*', default=[""],
        help='custom subtitle which will replace the actual subtitle')

    parser.add_argument(
        '--padding', dest='padding', type=float, nargs='*', default=PADDING,
        help=('padding to put around the quote in seconds: "1" or "0.5 1"; '
              'only up to two values are taken (default {})').format(PADDING))

    parser.add_argument(
        '--dither', dest='dither', type=int, nargs='?', default=DITHER,
        help='throw out every X frame (default: {})'.format(DITHER))

    parser.add_argument(
        '--no-quote', dest='quote', action='store_false',
        help=('this option will export the time between the end of this '
              'subtitle index and the start of the next one, it might be '
              'fairly long or broken (default: {})').format(True))
    parser.set_defaults(quote=True)

    parser.add_argument(
        '--filename', type=str, nargs='?', default="star_wars.gif",
        help='filename for the GIF (default: star_wars.gif)')

    parser.add_argument(
        '--palletsize', type=int, nargs='?', default=PALLETSIZE,
        help='Rounded to the next power of 2 (default: {})'.format(PALLETSIZE))

    parser.add_argument(
        '--width', type=int, nargs='?', default=WIDTH,
        help='width of the GIF (default: {})'.format(WIDTH))

    parser.add_argument(
        '--height', type=int, nargs='?', default=HEIGHT,
        help='height of the GIF (default: {})'.format(HEIGHT))

    parser.add_argument(
        '--frame_duration', type=float, nargs='?', default=FRAME_DURATION,
        help='duration each frame is shown in seconds (default: {})'.format(
            FRAME_DURATION
        ))

    parser.add_argument(
        '--frames', type=int, nargs='?', default=FRAMES,
        help='how many frames to export; 0 = unlimited (default: {})'.format(
            FRAMES
        ))

    parser.add_argument(
        '--font_path', type=str, nargs='?', default=FONT_PATH,
        help='path to font to use (default: {})'.format(
            FONT_PATH
        ))

    parser.add_argument(
        '--font_size', type=int, nargs='?', default=FONT_SIZE,
        help='size to render font in (default: {})'.format(
            FONT_SIZE
        ))

    parser.add_argument(
        '--config', type=str, nargs='?', default=CONFIG_FILE,
        help=('filename for the config, this only affects commandline ' +
              'calls (default: {})').format(CONFIG_FILE))

    # Parsing arguments
    args = parser.parse_args()
    CONFIG_FILE = args.config

    # by default we create a random gif
    makeGif(random.choice(args.movie), sub_index=args.index, quote=args.quote,
            filename=args.filename, frames=args.frames,
            padding=args.padding, dither=args.dither,
            width=args.width, height=args.height, palletsize=args.palletsize,
            frame_duration=args.frame_duration, custom_subtitle=args.subtitle,
            font_path=args.font_path, font_size=args.font_size,)
