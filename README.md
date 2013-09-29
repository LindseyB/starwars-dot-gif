Star Wars DOT Gif
-------------

**Note:** This code is entirely incomplete at this point and is rather messy. Sorry.

### To Use
Copy the contents of ```config.cfg.exmaple``` into ```config.cfg``` and make sure to change the paths for VLC and the Star Wars episodes. Any format that can be read by VLC should be acceptable for the movies.

Then you should be able to run

```
python makeGifs.py
```

Right now it will automatically open episode 4 and make the example gif ```star_wars.gif```.

If you would like to change this modify line 36, to be whatever episode you want and line 45 to match the correct .SRT file. Additionally, you can open the SRT file to find a quote and specify the index on line 48 (note: SRT files are 1 indexed, python lists are 0 indexed, subtract 1).

Also, you can definitely modify this to create gifs for just about anything with subtitles.

If generating gifs is taking too long for you remove ```nq=10``` from the ```writeGif``` call at the sacrifice of quality.