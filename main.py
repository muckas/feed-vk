import os
import time
import datetime
import vk_api
import telegram
import logging
from contextlib import suppress
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters
import db
import traceback
import vk_posts

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('')
log.setLevel(logging.DEBUG)

filename = datetime.datetime.now().strftime('%Y-%m-%d') + '.log'
file = logging.FileHandler(os.path.join('logs', filename))
file.setLevel(logging.DEBUG)
fileformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
file.setFormatter(fileformat)
log.addHandler(file)

stream = logging.StreamHandler()
stream.setLevel(logging.DEBUG)
streamformat = logging.Formatter('%(asctime)s:%(levelname)s: %(message)s')
stream.setFormatter(fileformat)
log.addHandler(stream)
# End of logger setup

with suppress(FileExistsError):
  os.makedirs('db')
  log.info('Created db folder')

vk_login = os.environ['VK_LOGIN']
vk_token = os.environ['VK_TOKEN']
tg_token = os.environ['TG_VKFEED_TOKEN']

log.info('Connecting to vk...')
vk_session = vk_api.VkApi(login=vk_login, token=vk_token)
vk_session.auth()
vk = vk_session.get_api()
log.info('Connected to vk')

log.info('Connecting to telegram...')
tg = telegram.Bot(tg_token)
tg.get_me()
log.info('Connected to telegram')

help_text = '''
Я буду слать тебе посты со стен групп или людей в VK
Отправь ссылку на группу или человека в VK, чтобы подписаться на ленту
/feed - показать список всех активных лент
/remove <ссылка на ленту> - удалить ленту, ссылку на ленту можно узнать командой /feed
'''

def start_command(update, context):
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if user_id not in users:
    chat = tg.getChat(user)
    username = chat['username']
    users.update({user_id:{'username':username}})
    db.write('users', users)
  help_command(update, context)

def help_command(update, context):
  if whitelisted(update.message.chat['id'], True):
    update.message.reply_text(help_text)

def add_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    url = update.message.text
    users = db.read('users')
    try:
      path, domain = url.split('https://vk.com/')
      group = vk.groups.getById(group_id=domain, fields='name')
      vk_id = int(group[0]['id']) * -1
      name = group[0]['name']
      if domain in users[user_id]['feeds']:
        update.message.reply_text(f'Группа "{name}" уже есть в ленте')
      else:
        posts = vk.wall.get(owner_id=vk_id, count=2)['items']
        last_id = posts[1]['id']
        users[user_id]['feeds'].update({domain:{'post_id':last_id, 'name':name, 'id':vk_id}})
        db.write('users', users)
        update.message.reply_text(f'Группа "{name}" добавлена в ленту')
    except vk_api.exceptions.ApiError as e:
      log.debug(f'Got {e} exception, handling...')
      path, domain = url.split('https://vk.com/')
      user = vk.users.get(user_ids=domain)
      vk_id = int(user[0]['id'])
      name = user[0]['first_name'] + ' ' + user[0]['last_name']
      if domain in users[user_id]['feeds']:
        update.message.reply_text(f'Пользователь "{name}" уже есть в ленте')
      else:
        posts = vk.wall.get(owner_id=vk_id, count=2)['items']
        last_id = posts[1]['id']
        users[user_id]['feeds'].update({domain:{'post_id':last_id, 'name':name, 'id':vk_id}})
        db.write('users', users)
        update.message.reply_text(f'Пользователь "{name}" добавлен в ленту')
    except ValueError:
      update.message.reply_text('Некорректная ссылка')

def show_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    users = db.read('users')
    if len(users[user_id]['feeds']) == 0:
      update.message.reply_text('Лента пуста')
    else:
      msg = 'Текущая лента:'
      i = 1
      for domain in users[user_id]['feeds']:
        name = users[user_id]['feeds'][domain]['name']
        msg += f'\n{i}: {name} https://vk.com/{domain}'
        i += 1
      update.message.reply_text(msg)

def remove_from_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    users = db.read('users')
    try:
      url = str(context.args[0])
      start, domain = url.split('https://vk.com/')
      if domain in users[user_id]['feeds']:
        name = users[user_id]['feeds'][domain]['name']
        users[user_id]['feeds'].pop(domain)
        db.write('users', users)
        update.message.reply_text(f'"{name}" больше не в ленте')
      else:
        update.message.reply_text('Такого в ленте нет')
        show_feed(update, context)
    except (IndexError, ValueError):
      update.message.reply_text('/remove <ссылка на ленту>')
      show_feed(update, context)


def whitelisted(user_id, notify=False):
  whitelist = db.read('whitelist')
  if db.read('params')['use_whitelist']:
    if user_id in whitelist:
      log.debug(f'User {user_id} whitelisted')
      return True
    else:
      log.debug(f'User {user_id} not whitelisted')
      if notify:
        tg.send_message(chat_id = user_id, text = f'Опа, а я тебя не знаю!\nТвой id - {user_id}')
      return False
  else:
    return True

def mainloop():
  try:
    while True:
      log.info('Started posts update...')
      users = db.read('users')
      params = db.read('params')
      for user in users:
        username = users[user]['username']
        log.info(f'Checking posts for user @{username} {user}...')
        if whitelisted(int(user)):
          for domain in users[user]['feeds']:
            last_post_id = users[user]['feeds'][domain]['post_id']
            name = users[user]['feeds'][domain]['name']
            vk_id = users[user]['feeds'][domain]['id']
            log.info(f'Checking {name} ({domain})...')
            posts = vk.wall.get(owner_id=vk_id, count=50)['items']
            posts.reverse()
            for post in posts:
              if post['id'] > last_post_id:
                log.info(f'New post from {name} ({domain}) with id {post["id"]} for user @{users[user]["username"]} ({user})')
                vk_posts.send(tg, user, post, name, domain, vk_id, post['id'])
                last_post_id = post['id']
                users[user]['feeds'][domain]['post_id'] = last_post_id
                db.write('users', users)
      update_period = params['update_period']
      log.info('Finished posts update')
      log.info(f'Sleeping for {update_period} seconds...')
      time.sleep(update_period)
  except Exception as e:
    log.error((traceback.format_exc()))
    return 0

if __name__ == '__main__':
  try:
    db.init('users')
    db.init('params')
    db.init('whitelist')
    updater = telegram.ext.Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_feed))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('feed', show_feed))
    dispatcher.add_handler(CommandHandler('remove', remove_from_feed))
    updater.start_polling()
    mainloop()
    log.error('Main thread ended, stopping updater...')
    updater.stop()
  except Exception as e:
    log.error((traceback.format_exc()))
