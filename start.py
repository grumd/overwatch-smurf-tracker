import json
import cv2
import psutil
import numpy as np
import os, time
import pytesseract_v2 as pytesseract
import sys, traceback
import importlib
import win32process
import win32gui
import threading
import ctypes
from sty import bg
from pathlib import Path

from screen_recorder_sdk import screen_recorder

if sys.platform == "win32":
  os.system('color')

config_number = f"--psm 7 -c tessedit_char_whitelist=0123456789"
config_text = f"--psm 7"

# constants
victory = 'W'
defeat = 'L'
draw = 'D'

# scoreboard values
my_team_template = {
  'x': 890,
  'y': 330,
  'w': 173,
  'h': 34,
  'template': cv2.imread('./templates/my_team.png'),
  'mask': None,
}
scoreboard_template = {
  'x': 161,
  'y': 393,
  'w': 139,
  'h': 195,
  'template': cv2.imread('./templates/scoreboard.png'),
  'mask': None,
}
victory_template = {
  'x': 998,
  'y': 365,
  'w': 581,
  'h': 168,
  'template': cv2.imread('./templates/victory.png'),
  'mask': cv2.imread('./templates/victory_mask.png'),
}
defeat_template = {
  'x': 1050,
  'y': 367,
  'w': 463,
  'h': 166,
  'template': cv2.imread('./templates/defeat.png'),
  'mask': cv2.imread('./templates/defeat_mask.png'),
}
draw_template = {
  'x': 1074,
  'y': 366,
  'w': 419,
  'h': 167,
  'template': cv2.imread('./templates/draw.png'),
  'mask': cv2.imread('./templates/draw_mask.png'),
}
# coordinates for level boxes
level_boxes_top_left = [
  # my team
  (989, 435),
  (989, 542),
  (989, 648),
  (989, 755),
  (989, 862),
  (989, 968),
  # enemies
  (1726, 435),
  (1726, 542),
  (1726, 648),
  (1726, 755),
  (1726, 862),
  (1726, 968),
]
# colors
border_colors = (
  [61, 98, 193],
  [236, 230, 213],
  [19, 205, 251],
  [252, 218, 208]
)
border_color_names = (
  'bronze',
  'silver',
  'gold',
  'diamond',
)
print_colors = (
  bg(130),
  bg(243),
  bg(214),
  bg(69),
)
border_level_add = (
  0,
  600,
  1200,
  2400,
)

def get_pid_state(pid):
  state = None
  windows = []
  def callback(hwnd, arg):
    windows.append(hwnd)
  win32gui.EnumWindows(callback, None)
  for hwnd in windows:
    if pid in win32process.GetWindowThreadProcessId(hwnd):
      placement = win32gui.GetWindowPlacement(hwnd)
      if placement[4][2] == 2560 and placement[4][3] == 1440:
        state = placement[1]
  return state

def get_pixel_diff(pixel1, pixel2):
  return max(abs(int(pixel1[0]) - int(pixel2[0])), abs(int(pixel1[1]) - int(pixel2[1])), abs(int(pixel1[2]) - int(pixel2[2])))

def is_matched(image, template, threshold = 0.99):
  crop = image[template['y'] : template['y'] + template['h'], template['x'] : template['x'] + template['w']]
  if template['mask'] is not None:
    res = cv2.matchTemplate(crop, template['template'], cv2.TM_CCORR_NORMED, mask=template['mask'])
  else:
    res = cv2.matchTemplate(crop, template['template'], cv2.TM_CCORR_NORMED)
  maxVal = cv2.minMaxLoc(res)[1]
  return maxVal >= threshold, maxVal

def is_star_bg(pixel):
  return pixel[0] > 245 and pixel[1] > 245 and pixel[2] > 245

def find_color_index(pixel):
  for i in range(len(border_colors)):
    if get_pixel_diff(pixel, border_colors[i]) < 5:
      return i

def match_result(img):
  maxValue = 0
  match, value = is_matched(img, victory_template)
  maxValue = max(value, maxValue)
  if match:
    return victory, value
  match, value = is_matched(img, defeat_template)
  maxValue = max(value, maxValue)
  if match:
    return defeat, value
  match, value = is_matched(img, draw_template)
  maxValue = max(value, maxValue)
  if match:
    return draw, value
  return None, maxValue

def recognize_scoreboard(img):
  players = []
  for player_number in range(12):
    # print(f"-- Player {player_number}")
    left_dot = level_boxes_top_left[player_number]
    width_to_check = 52
    first_pixel = img[left_dot[1], left_dot[0]]
    prev_stable_pixel = img[left_dot[1], left_dot[0]]
    stable_offsets = []
    stars = -1
    star_bg_start = -1
    # print(f"-- First pixel {first_pixel}")
    for width_offset in range(width_to_check):
      current_pixel = img[left_dot[1], left_dot[0] + width_offset]
      next_pixel = img[left_dot[1], left_dot[0] + width_offset + 1]
      next_next_pixel = img[left_dot[1], left_dot[0] + width_offset + 2]
      if get_pixel_diff(current_pixel, first_pixel) < 5 and stable_offsets:
        # Got to background again, end the loop
        # print(f"Offset {width_offset}")
        # print(f"Background condition abort")
        stars = 0
        stable_offsets.append(width_offset)
        break
      diff = get_pixel_diff(current_pixel, prev_stable_pixel)
      diff_next = get_pixel_diff(current_pixel, next_pixel)
      diff_next_next = get_pixel_diff(next_pixel, next_next_pixel)
      if diff > 35 and diff_next < 10 and diff_next_next < 10:
        # print(f"Offset {width_offset}, {current_pixel}")
        # print(f"New stable pixel")
        if is_star_bg(current_pixel):
          # print(f"Found white pixel")
          star_bg_start = width_offset
        stable_offsets.append(width_offset)
        prev_stable_pixel = img[left_dot[1], left_dot[0] + width_offset]
    # print(f"Stable offsets: {stable_offsets}")
    if star_bg_start > 0:
      start_pixel = img[left_dot[1], left_dot[0] + star_bg_start]
      star_bg_offset = 0
      while 10 > get_pixel_diff(start_pixel, img[left_dot[1], left_dot[0] + star_bg_start + star_bg_offset]):
        star_bg_offset += 1
      # print(f"Start p: {start_pixel}, End p: {img[left_dot[1], left_dot[0] + star_bg_start + star_bg_offset]}")
      star_bg_end = star_bg_start + star_bg_offset
      stars = round((star_bg_offset - 2) / 10)
    player_level_crop = img[left_dot[1] - 1 : left_dot[1] + 16, left_dot[0] + stable_offsets[0] + 3 : left_dot[0] + stable_offsets[1] - 3]
    border_color = player_level_crop[0, 0]
    color_index = find_color_index(border_color)
    color = '?'
    level_add = 0
    print_color = bg(0)
    if color_index is not None:
      color = border_color_names[color_index]
      print_color = print_colors[color_index]
      level_add = border_level_add[color_index]
    else:
      print(f"Unknown color {border_color}")
    
    player_level_crop = cv2.resize(player_level_crop, (player_level_crop.shape[1] * 4, player_level_crop.shape[0] * 4), interpolation = cv2.INTER_LANCZOS4)
    if (color == 'bronze'):
      player_level_crop = cv2.bitwise_not(player_level_crop)
    player_level_crop = cv2.cvtColor(player_level_crop, cv2.COLOR_BGR2GRAY)
    player_level_crop = cv2.adaptiveThreshold(player_level_crop,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,71,10)
    player_level = pytesseract.image_to_string(player_level_crop, config=config_number)
    if player_level == '':
      player_level = '0'
    # cv2.imwrite(f'./numbers/{player_number}_{player_level}.png', player_level_crop)
    players.append({ 'level': player_level, 'level_base': level_add, 'color': color, 'stars': stars })
    # print(f"Level: {player_level}, Stars: {stars}, Color: {border_color}")
  print("  My team                 Enemy team")
  for i in range(6):
    # print(f"- Player {i + 1}:\t\t- Player {i + 7}")
    print_color_left = print_colors[border_color_names.index(players[i]['color'])]
    print_color_right = print_colors[border_color_names.index(players[i+6]['color'])]
    part1 = f"- {print_color_left}{players[i]['level']} {'*' * players[i]['stars']}{bg.rs}                  "[:29]
    part2 = f"- {print_color_right}{players[i+6]['level']} {'*' * players[i+6]['stars']}{bg.rs}              "[:29]
    part1 += f"{players[i]['color']}      "[:10]
    part2 += f"{players[i+6]['color']}    "[:10]
    print(f"{part1} {part2}")
    # print(f"{part1} {part2}")
  return players

def find_pid_by_name(process_name):
  '''
  Get a list of all the PIDs of a all the running process whose name contains
  the given string process_name
  '''
  process_objects = []
  # Iterate over the all the running process
  for proc in psutil.process_iter():
    try:
      pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
      # Check if process name contains the given name string.
      if process_name.lower() in pinfo['name'].lower():
        process_objects.append(pinfo)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
      pass
  return process_objects;

def pil_to_cv2_image(pil_image):
  return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

def get_pid():
  overwatch_pid = None
  while overwatch_pid is None:
    processes = find_pid_by_name('overwatch.exe')
    if processes:
      overwatch_pid = processes[0]['pid']
    else:
      time.sleep(3)
  return overwatch_pid

def restart_program():
  """Restarts the current program, with file objects and descriptors
      cleanup
  """
  python = sys.executable
  os.execl(python, python, *sys.argv)

# Definitions
waiting_for = 'scoreboard'
current_match = None
pause_between_screenshots = 1

def save_state():
  global waiting_for, current_match
  with open('state.json', 'w') as f:
    json.dump({ 'waiting_for': waiting_for, 'current_match': current_match }, f, indent=1)

def load_state():
  global waiting_for, current_match
  with open('state.json') as f:
    state = json.load(f)
    waiting_for = state['waiting_for']
    current_match = state['current_match']

def ensure_file_structure():
  global waiting_for, current_match
  if not os.path.isfile('state.json'):
    with open('state.json', 'w') as f:
      json.dump({ 'waiting_for': waiting_for, 'current_match': current_match }, f)
  if not os.path.isfile('results.json'):
    with open('results.json', 'w') as f:
      json.dump([], f)
  if not os.path.isfile('results_short.json'):
    with open('results_short.json', 'w') as f:
      json.dump([], f)
  Path("./scoreboards").mkdir(parents=True, exist_ok=True)
  Path("./scoreboards_errors").mkdir(parents=True, exist_ok=True)

def get_player_level(player):
  return player['level_base'] + int(player['level']) + player['stars'] * 100

def get_player_readable_tuple(player):
  level = get_player_level(player)
  return (level, f"{border_color_names.index(player['color'])}-{player['level']}-{'*' * player['stars']}")

last_log = []
def log(*args):
  global last_log
  if args != last_log:
    print(*args)
    last_log = args

def main():
  if ctypes.windll.shell32.IsUserAnAdmin() == 0:
    log('Please run as administrator')
    exit(0)
  
  global waiting_for, current_match, pause_between_screenshots
  ensure_file_structure()

  log('-- Searching for Overwatch.exe')
  overwatch_pid = get_pid()
  log('-- Overwatch PID is', overwatch_pid)
  while get_pid_state(overwatch_pid) == 2:
    log('-- Overwatch is minimized')
    time.sleep(5)
  log('-- Overwatch is open, initializing')
  time.sleep(4) # Pause before initializing
  # screen_recorder.enable_dev_log()
  screen_recorder.disable_log()
  screen_recorder.init_resources(overwatch_pid)
  log('-- Initialized resources')
  load_state()
  log('-- Loaded state:', waiting_for, current_match['scoreboard_file'] if current_match is not None else None)
  
  while True:
    cycle_time = time.strftime("%Y-%m-%d-%H-%M-%S");
    time.sleep(pause_between_screenshots)
    pil_image = None

    pid_state = get_pid_state(overwatch_pid)
    if pid_state == 2:
      log('-- Overwatch is minimized')
      time.sleep(5)
      continue
    if pid_state is None:
      log('Overwatch has closed')
      exit(0)

    try:
      pil_image = screen_recorder.get_screenshot(1)
    except screen_recorder.RecorderError as err:
      log(f"Error taking screenshot", err)
      restart_program()
    if pil_image:
      img = pil_to_cv2_image(pil_image)
      if waiting_for == 'scoreboard':
        log('-- Waiting for a SCOREBOARD')
        match, value = is_matched(img, scoreboard_template)
        if match:
          log('Found scoreboard', match, value)
          # This screenshot shows scoreboard
          try:
            filename = f'./scoreboards/scoreboard_{cycle_time}.png'
            players = recognize_scoreboard(img)
            current_match = { 'scoreboard_file': filename, 'players': players }
            waiting_for = 'result'
            cv2.imwrite(filename, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            save_state()
          except:
            filename = f'./scoreboards_errors/scoreboard_{cycle_time}.png'
            cv2.imwrite(filename, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            traceback.print_exc(file=sys.stdout)
            log(f"Error recognizing {filename}")
      if waiting_for == 'result':
        log('-- Waiting for a RESULT')
        result, value = match_result(img)
        if result is not None:
          log(f"Found result: {result}, confidence: {value}")
          filename = current_match['scoreboard_file'].replace('scoreboard_', 'scoreboard_result_')
          cv2.imwrite(filename, img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
          with open("results.json", "r+") as file:
            results_array = json.load(file)
            results_array.append({ 'result': result, 'result_file': filename, 'scoreboard_file': current_match['scoreboard_file'], 'players': current_match['players'] })
            file.seek(0)
            json.dump(results_array, file, indent=1)
          with open("results_short.json", "r+") as file:
            results_array = json.load(file)
            results_array.append({ 'result': result, 'result_file': filename, 'players': list(map(get_player_level, current_match['players'])) })
            file.seek(0)
            json.dump(results_array, file, indent=1)
          waiting_for = 'scoreboard'
          current_match = None
          save_state()

if __name__ == "__main__":
  main()