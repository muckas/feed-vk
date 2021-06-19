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
from retry import retry

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
vk_password = os.environ['VK_PASSWORD']
tg_token = os.environ['TG_VKFEED_TOKEN']
tg_userid = os.environ['TG_USERID']

log.info('Connecting to vk...')
vk_session = vk_api.VkApi(vk_login , vk_password)
vk_session.auth()
vk = vk_session.get_api()
log.info('Connected to vk')

log.info('Connecting to telegram...')
tg = telegram.Bot(tg_token)
tg.get_me()
log.info('Connected to telegram')

def send_post(user_id, post, poster_name, domain):
  msg_text = ''
  msg_attachments = []
  post_id = post['id']
  post_text = post['text']
  msg_text = post_text + '\n----------------------------\n' + poster_name + '\nhttps://vk.com/' + domain
  if 'attachments' in post.keys():
    attachments = post['attachments']
    for attachment in attachments:
      if attachment['type'] == 'photo':
        sizes = attachment['photo']['sizes']
        photo = sorted(sizes, key = lambda item: item['height'])[-1]
        msg_attachments.append(photo['url'])
  if len(msg_attachments) > 1:
    msg_photos = []
    for photo in msg_attachments:
      if photo is msg_attachments[0]:
        msg_photos.append(telegram.InputMediaPhoto(media=photo, caption=msg_text))
      else:
        msg_photos.append(telegram.InputMediaPhoto(media=photo))
    tg.sendMediaGroup(chat_id=tg_userid, media=msg_photos)
  elif len(msg_attachments) == 1:
    tg.send_photo(chat_id=tg_userid, photo=msg_attachments[0], caption=msg_text)
  else:
    tg.send_message(chat_id=tg_userid, text=msg_text)

help_text = '''
Я буду слать тебе посты со стен групп или людей в VK
Отправь ссылку на группу или человека в VK, чтобы подписаться на ленту
/feed - показать список всех активных лент
/remove <ссылка на ленту> - удалить ленту, ссылку на ленту можно узнать командой /feed
'''

def start_command(update, context):
  help_command(update, context)

def help_command(update, context):
  if whitelisted(update.message.chat['id']):
    update.message.reply_text(help_text)

def add_feed(update, context):
  if whitelisted(update.message.chat['id']):
    user_id = str(update.message.chat['id'])
    url = update.message.text
    settings = db.read()
    try:
      path, domain = url.split('https://vk.com/')
      group = vk.groups.getById(group_id=domain, fields='name')
      name = group[0]['name']
      if user_id not in settings['users']:
        settings['users'].update({user_id:{}})
      if domain in settings['users'][user_id]:
        update.message.reply_text(f'Группа "{name}" уже есть в ленте')
      else:
        posts = vk.wall.get(domain=domain, count=2)['items']
        last_id = posts[1]['id']
        settings['users'][user_id].update({domain:{'post_id':last_id, 'name':name}})
        db.write(settings)
        update.message.reply_text(f'Группа "{name}" добавлена в ленту')
    except vk_api.exceptions.ApiError:
      path, domain = url.split('https://vk.com/')
      user = vk.users.get(user_ids=domain)
      name = user[0]['first_name'] + ' ' + user[0]['last_name']
      if user_id not in settings['users']:
        settings['users'].update({user_id:{}})
      if domain in settings['users'][user_id]:
        update.message.reply_text(f'Пользователь "{name}" уже есть в ленте')
      else:
        posts = vk.wall.get(domain=domain, count=1)['items']
        last_id = posts[0]['id']
        settings['users'][user_id].update({domain:{'post_id':last_id, 'name':name}})
        db.write(settings)
        update.message.reply_text(f'Пользователь "{name}" добавлен в ленту')
    except ValueError:
      update.message.reply_text('Некорректная ссылка')

def show_feed(update, context):
  if whitelisted(update.message.chat['id']):
    user_id = str(update.message.chat['id'])
    settings = db.read()
    if len(settings['users'][user_id]) == 0:
      update.message.reply_text('Лента пуста')
    else:
      msg = 'Текущая лента:'
      i = 1
      for group in settings['users'][user_id]:
        print(group)
        msg += f'\n{i}: {settings["users"][user_id][group]["name"]} https://vk.com/{group}'
        i += 1
      update.message.reply_text(msg)

def remove_from_feed(update, context):
  if whitelisted(update.message.chat['id']):
    user_id = str(update.message.chat['id'])
    settings = db.read()
    try:
      url = str(context.args[0])
      start, domain = url.split('https://vk.com/')
      if domain in settings['users'][user_id]:
        name = settings['users'][user_id][domain]['name']
        settings['users'][user_id].pop(domain)
        db.write(settings)
        update.message.reply_text(f'"{name}" больше не в ленте')
      else:
        update.message.reply_text('Такого в ленте нет')
        show_feed(update, context)
    except (IndexError, ValueError):
      update.message.reply_text('/remove <ссылка на ленту>')
      show_feed(update, context)


def whitelisted(userid):
  settings = db.read()
  if settings['params']['use_whitelist']:
    if userid in settings['whitelist']:
      return True
    else:
      tg.send_message(chat_id = userid, text = f'Опа, а я тебя не знаю!\nТвой id - {userid}')
      return False
  else:
    return True

@retry(exceptions=Exception, tries=-1, delay=0)
def mainloop():
  while True:
    log.info('Started posts update...')
    settings = db.read()
    for user in settings['users']:
      for domain in settings['users'][user]:
        last_post_id = settings['users'][user][domain]['post_id']
        name = settings['users'][user][domain]['name']
        posts = vk.wall.get(domain=domain, count=50)['items']
        posts.reverse()
        for post in posts:
          if post['id'] > last_post_id:
            log.info(f'New post from {name} ({domain}) with id {post["id"]} for user {user}')
            send_post(user, post, name, domain)
            last_post_id = post['id']
            settings['users'][user][domain]['post_id'] = last_post_id
            db.write(settings)
    update_period = settings['params']['update_period']
    log.info(f'Sleeping for {update_period} seconds...')
    time.sleep(update_period)

if __name__ == '__main__':
  try:
    db.init()
    updater = telegram.ext.Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_feed))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('feed', show_feed))
    dispatcher.add_handler(CommandHandler('remove', remove_from_feed))
    updater.start_polling()
    mainloop()
    updater.idle()
  except Exception as e:
    log.error((traceback.format_exc()))
