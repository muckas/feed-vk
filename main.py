import os
import datetime
import vk_api
import telegram
import logging
from contextlib import suppress
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters
import db
import traceback

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

# posts = vk.wall.get(domain='fest', count=1)['items']
#
# for post in posts:
#   msg_text = ''
#   msg_attachments = []
#   post_id = post['id']
#   post_text = post['text']
#   msg_text = post_text
#   if 'attachments' in post.keys():
#     attachments = post['attachments']
#     for attachment in attachments:
#       if attachment['type'] == 'photo':
#         sizes = attachment['photo']['sizes']
#         photo = sorted(sizes, key = lambda item: item['height'])[-1]
#         msg_attachments.append(photo['url'])
#   if len(msg_attachments) > 1:
#     msg_photos = []
#     for photo in msg_attachments:
#       if photo is msg_attachments[0]:
#         msg_photos.append(telegram.InputMediaPhoto(media=photo, caption=msg_text))
#       else:
#         msg_photos.append(telegram.InputMediaPhoto(media=photo))
#     tg.sendMediaGroup(chat_id=tg_userid, media=msg_photos)
#   elif len(msg_attachments) == 1:
#     tg.send_photo(chat_id=tg_userid, photo=msg_attachments[0], caption=msg_text)
#   else:
#     tg.send_message(chat_id=tg_userid, text=msg_text)

help_text = '''
Я буду слать тебе посты со стен групп или людей в VK
Отправь ссылку на группу или человека в VK, чтобы подписаться на ленту
/feed - показать список всех активных лент
/remove <номер> - удалить ленту, номер ленты можно узнать командой /feed
'''

def start_command(update, context):
  help_command(update, context)

def help_command(update, context):
  if whitelisted(update.message.chat['id']):
    update.message.reply_text(help_text)

def add_feed(update, context):
  if whitelisted(update.message.chat['id']):
    user_id = update.message.chat['id']
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
        settings['users'][user_id].update({domain:{'post_id':0, 'name':name}})
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
        settings['users'][user_id].update({domain:{'post_id':0, 'name':name}})
        db.write(settings)
        update.message.reply_text(f'Пользователь "{name}" добавлен в ленту')
    except ValueError:
      update.message.reply_text('Некорректная ссылка')


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

if __name__ == '__main__':
  try:
    db.init()
    updater = telegram.ext.Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_feed))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('start', start_command))
    updater.start_polling()
    updater.idle()
  except Exception as e:
    log.error((traceback.format_exc()))
