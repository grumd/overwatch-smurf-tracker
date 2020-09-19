# overwatch-smurf-tracker
A script I made in python for myself.
Tracks Overwatch matches - levels of your team and enemies, and tracks if you win/lose/draw.

How to run this:

1. Run the script with `python start.py` or run the `run.sh` script with bash
2. When in a competitive game, press P to open the list of players. The script will automatically detect enemies' and your team account levels.
3. Script will start waiting for Victory/Defeat/Draw screen. Will detect it automatically. Just don't exit the server too soon.
4. Stats will be recorded in the json files.

It's not perfect but it works for me. Highly suggested to run the script on a second monitor, you won't be able to see if it failed or whatever.
