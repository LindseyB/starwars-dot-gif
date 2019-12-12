#!env python

import ast
import configparser
import pysrt
import urwid
from make_gifs import make_gif, check_config

config = configparser.ConfigParser()
config.read("config.cfg")
config.sections()
(ffmpeg_path, vlc_path, movies, slugs) = check_config("config.cfg")

selected_movie = None
index = 0
subtitle = ""


def menu(title, movies):
    body = [urwid.Text(title), urwid.Divider()]
    button = urwid.Button('All movies (might take a long time)')
    urwid.connect_signal(button, 'click', item_chosen, 'all')
    body.append(urwid.AttrMap(button, None, focus_map='reversed'))
    for m in movies:
        button = urwid.Button(m['title'])
        urwid.connect_signal(button, 'click', item_chosen, m)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


def item_chosen(button, movie):
    global selected_movie

    if movie == 'all':
        response = urwid.Text([u'You chose ', 'all movies', u'\n'])
    else:
        response = urwid.Text([u'You chose ', movie['title'], u'\n'])
    selected_movie = movie
    done = urwid.Button(u'Ok')
    urwid.connect_signal(done, 'click', search)
    main.original_widget = urwid.Filler(urwid.Pile(
        [response, urwid.AttrMap(done, None, focus_map='reversed')]))

# TODO: Add enter as "send" -> QuestionBox in Tutorial


def search(button):
    edit = urwid.Edit("Search quotes: ")
    done = urwid.Button(u'Search')
    urwid.connect_signal(done, 'click', find_quotes, edit)
    exit_button = urwid.Button(u'Exit')
    urwid.connect_signal(exit_button, 'click', exit)
    main.original_widget = urwid.Filler(urwid.Pile([
        edit,
        urwid.AttrMap(done, None, focus_map='reversed'),
        urwid.AttrMap(exit_button, None, focus_map='reversed')]))


def find_quotes(button, edit):
    if selected_movie == 'all':
        subs = []
        for movie in movies:
            subs.extend([
                (movie, quote) for quote in pysrt.open(movie['subtitle_path'])
            ])
    else:
        subs = [
            (selected_movie,
             quote) for quote in pysrt.open(selected_movie['subtitle_path'])]
    search_text = edit.edit_text.lower()

    def seek(item, quote):
        for i in item.split(' '):
            if i in quote:
                return True
        return False
    matching = [(m, s) for (m, s) in subs if seek(search_text, s.text.lower())]

    if len(matching) > 0:
        body_text = "Select quote ({} matches found)".format(len(matching))
    else:
        body_text = "No quotes found"
    body = [urwid.Text(body_text), urwid.Divider()]
    for movie_tuple in matching:
        (m, s) = movie_tuple
        if selected_movie == 'all':
            button = urwid.Button('{}: {}'.format(m['title'], s.text))
        else:
            button = urwid.Button(s.text)
        urwid.connect_signal(
            button, 'click', add_custom_subtitle, movie_tuple)
        body.append(urwid.AttrMap(button, None, focus_map='reversed'))

    back_button = urwid.Button('Go back')
    urwid.connect_signal(back_button, 'click', search)
    body.append(urwid.AttrMap(back_button, None, focus_map='reversed'))
    main.original_widget = urwid.ListBox(urwid.SimpleFocusListWalker(body))


def add_custom_subtitle(button, movie_tuple):
    global index, selected_movie
    (m, s) = movie_tuple
    index = s.index
    # if we searched in all movies, we have to set proper movie now
    if selected_movie == 'all':
        selected_movie = m
    body = [urwid.Text("Add a custom quote?"), urwid.Divider()]
    yes_button = urwid.Button("Yes")
    urwid.connect_signal(yes_button, 'click', enter_custom_subtitle)
    body.append(urwid.AttrMap(yes_button, None, focus_map='reversed'))
    no_button = urwid.Button("No")
    urwid.connect_signal(no_button, 'click', generate_gif)
    body.append(urwid.AttrMap(no_button, None, focus_map='reversed'))
    main.original_widget = urwid.ListBox(urwid.SimpleFocusListWalker(body))


def enter_custom_subtitle(button):
    subtitle = urwid.Edit("Enter custom subtitle: ")
    done = urwid.Button(u'Submit')
    urwid.connect_signal(done, 'click', generate_gif_with_subtitle, subtitle)
    main.original_widget = urwid.Filler(urwid.Pile([
        subtitle, urwid.AttrMap(done, None, focus_map='reversed')]))


def generate_gif(button):
    raise urwid.ExitMainLoop()


def generate_gif_with_subtitle(button, edit):
    global subtitle
    subtitle = edit.edit_text
    raise urwid.ExitMainLoop()


def exit(button):
    global index
    index = None
    raise urwid.ExitMainLoop()

main = urwid.Padding(menu(u'Movie choice', movies), left=2, right=2)
top = urwid.Overlay(main, urwid.SolidFill(
    u'\N{MEDIUM SHADE}'),
    align='center', width=('relative', 60),
    valign='middle', height=('relative', 60),
    min_width=20, min_height=9)
urwid.MainLoop(top, palette=[('reversed', 'standout', '')]).run()
if index:
    make_gif(selected_movie['slug'], [index], custom_subtitle=[subtitle])
