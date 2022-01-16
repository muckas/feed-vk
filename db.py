import os
import json
import logging

log = logging.getLogger('main')

def init(name):
  log.debug(f'Initializing {name}.json')
  if os.path.isfile(os.path.join('db', f'{name}.json')):
    log.debug(f'{name}.json exists')
    return read(name)
  else:
    defaults = read(f'{name}.defaults')
    if defaults:
      log.debug(f'Writing defaults to {name}.json')
      write(name, defaults)
      return defaults
    else:
      log.debug(f'Writing empty {name}.json')
      with open(os.path.join('db',f'{name}.json'), 'x') as f:
        json_obj = {}
        json_obj = json.dumps(defaults, indent=2)
        f.write(json_obj)
    return read(name)

def read(name):
  log.debug(f'Reading from {name}.json')
  try:
    with open(os.path.join('db',f'{name}.json'), 'r') as f:
      content = json.load(f)
    if content:
      return content
    else:
      return {}
  except FileNotFoundError:
    log.debug(f'{name}.json does not exist')
    return None

def write(name, content):
  log.debug(f'Writing to {name}.json')
  with open(os.path.join('db',f'{name}.json'), 'w') as f:
    json_obj = json.dumps(content, indent=2)
    f.write(json_obj)
