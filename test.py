import json
import cv2
import psutil
import numpy as np
import os, time
import pytesseract_v2 as pytesseract
import sys, traceback
import importlib

from screen_recorder_sdk import screen_recorder

import start

print(start.recognize_scoreboard(cv2.imread('./scoreboards_errors/scoreboard_2020-08-15-02-57-52.png')))
print(start.recognize_scoreboard(cv2.imread('./scoreboards_errors/scoreboard_2020-08-12-01-59-46.png')))