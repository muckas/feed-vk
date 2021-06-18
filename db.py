import os
import json

def init():
  try:
    with open(os.path.join('db','db.json'), 'x') as f:
      defaults = {
          'params':{
            'update_period':300,
            'use_whitelist':False
            },
          'whitelist':[],
          'users':{},
          }
      json_obj = json.dumps(defaults, indent=2)
      f.write(json_obj)
      return defaults
  except FileExistsError:
    return read()

def read():
  with open(os.path.join('db','db.json'), 'r') as f:
    settings = json.load(f)
  return settings

def write(settings):
  with open(os.path.join('db','db.json'), 'w') as f:
    json_obj = json.dumps(settings, indent=2)
    f.write(json_obj)
