import json
import cv2
import psutil
import numpy as np
import os, time
import pytesseract_v2 as pytesseract
import sys, traceback
import importlib
from os import listdir
from os.path import isfile, join, exists
from shutil import copyfile

from screen_recorder_sdk import screen_recorder

import start

# print(start.recognize_scoreboard(cv2.imread('./scoreboards/scoreboard_2020-08-12-01-48-38.png')))

path = './scoreboards'
scoreboards = [f for f in listdir(path) if isfile(join(path, f)) and f.startswith('scoreboard') and not f.startswith('scoreboard_result')]
results = [f for f in listdir(path) if isfile(join(path, f)) and f.startswith('scoreboard_result')]

results_array = []
results_short_array = []

for scoreboard_file in scoreboards:
  date_text = scoreboard_file.replace('scoreboard_', '').replace('.png', '')
  result_file = next((r for r in results if r.find(date_text) > -1), None)
  if result_file is not None:
    print('File:', scoreboard_file)
    img = cv2.imread(join(path, scoreboard_file))
    img_res = cv2.imread(join(path, result_file))
    players = start.recognize_scoreboard(img)
    result, value = start.match_result(img_res)
    print('Result:', result)
    results_array.append({ 'result': result, 'players': players, 'result_file': result_file, 'scoreboard_file': scoreboard_file })
    results_short_array.append({ 'result': result, 'result_file': result_file, 'players': list(map(start.get_player_level, players)) })

if exists('results.json'):
  copyfile('results.json', 'results_backup.json')
if exists('results_short.json'):
  copyfile('results_short.json', 'results_short_backup.json')

with open('results.json', 'w') as file:
  json.dump(results_array, file, indent=1)

with open("results_short.json", "w") as file:
  json.dump(results_short_array, file, indent=1)
