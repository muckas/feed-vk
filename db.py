import os
import json

def init(name):
  try:
    with open(os.path.join('db',f'{name}.json'), 'x') as f:
      json_obj = {}
      json_obj = json.dumps(defaults, indent=2)
      f.write(json_obj)
    return read(name)
  except FileExistsError:
    return read(name)

def read(name):
  with open(os.path.join('db',f'{name}.json'), 'r') as f:
    content = json.load(f)
  return content

def write(name, content):
  with open(os.path.join('db',f'{name}.json'), 'w') as f:
    json_obj = json.dumps(content, indent=2)
    f.write(json_obj)
