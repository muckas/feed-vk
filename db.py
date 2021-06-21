import os
import json
import logging

log = logging.getLogger()

def init(name):
  log.debug(f'Initializing {name} db')
  try:
    with open(os.path.join('db',f'{name}.json'), 'x') as f:
      json_obj = {}
      json_obj = json.dumps(defaults, indent=2)
      f.write(json_obj)
    return read(name)
  except FileExistsError:
    return read(name)

def read(name):
  log.debug(f'Reading from {name} db')
  with open(os.path.join('db',f'{name}.json'), 'r') as f:
    content = json.load(f)
  return content

def write(name, content):
  log.debug(f'Writing to {name} db')
  with open(os.path.join('db',f'{name}.json'), 'w') as f:
    json_obj = json.dumps(content, indent=2)
    f.write(json_obj)
