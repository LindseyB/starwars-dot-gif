Star Wars DOT Gif
-------------

### To Use
Copy the contents of ```config.cfg.exmaple``` into ```config.cfg``` and make sure to change the paths for VLC and the Star Wars episodes. Any format that can be read by VLC should be acceptable for the movies.

To Run with search UI:

```
$ python star_wars_gif.py
```

To get a random gif:

```
$ python makeGifs.py
```

If you want to use ```makeGifs``` elsewhere use:

```
from makeGifs import makeGif
# source should be 4, 5, or 6
# index is the index of the SRT
makeGif(source, index)
```