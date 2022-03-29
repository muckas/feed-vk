import os
import sys
import getopt
import time
import datetime
import vk_api
import logging
from contextlib import suppress
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import telegram.ext
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackQueryHandler
import db
import traceback
import vk_posts

VERSION = '0.10.0'

# Logger setup
with suppress(FileExistsError):
  os.makedirs('logs')
  print('Created logs folder')

log = logging.getLogger('main')
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

tg_token = None
vk_login = None
vk_password = None

try:
  args, values = getopt.getopt(sys.argv[1:],"h",["tg-token=","vk-login=","vk-password="])
  for arg, value in args:
    if arg in ('--tg-token'):
      tg_token = value
    if arg in ('--vk-login'):
      vk_login = value
    if arg in ('--vk-password'):
      vk_password = value
except getopt.GetoptError:
  print('-h, --tg-token, --vk-login, --vk-password')
  sys.exit(2)

log.info('=============================')
log.info(f'VK Feed v{VERSION} start')

with suppress(FileExistsError):
  os.makedirs('db')
  log.info('Created db folder')

try:
  if not vk_login:
    vk_login = os.environ['VK_LOGIN']
  if not vk_password:
    vk_password = os.environ['VK_PASSWORD']
  if not tg_token:
    tg_token = os.environ['TG_TOKEN']

  log.info('Connecting to vk...')
  vk_session = vk_api.VkApi(login=vk_login, password=vk_password, api_version='5.130')
  vk_session.auth()
  vk = vk_session.get_api()
  log.info('Connected to vk')

  log.info('Connecting to telegram...')
  tg = telegram.Bot(tg_token)
  tg.get_me()
  log.info('Connected to telegram')
except Exception:
  log.error(traceback.format_exc())
  sys.exit(2)

help_text = '''
Отправь ссылку на группу или человека в VK, чтобы подписаться на ленту
/feed - показать список всех активных лент
/remove <ссылка на ленту> - удалить ленту, ссылку на ленту можно узнать командой /feed
'''

def add_user_to_db(user_id, update):
  log.info(f'Adding new user {user_id} to database')
  users = db.read('users')
  tg_username = str(update.message.chat['username'])
  users.update({user_id:{'username':tg_username, 'feeds':{}}})
  db.write('users', users)
  log.info(f'Added {tg_username} to database')

def start_command(update, context):
  user_id = str(update.message.chat['id'])
  users = db.read('users')
  if user_id not in users:
    add_user_to_db(user_id)
  help_command(update, context)

def help_command(update, context):
  if whitelisted(update.message.chat['id'], True):
    update.message.reply_text(help_text)

def add_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    url = update.message.text
    users = db.read('users')
    if user_id not in users:
      add_user_to_db(user_id, update)
      users = db.read('users')
    try:
      domain = url.split('/')[-1]
      group = vk.groups.getById(group_id=domain)
      vk_id = int(group[0]['id']) * -1
      name = group[0]['name']
      if domain in users[user_id]['feeds']:
        update.message.reply_text(f'Группа "{name}" уже есть в ленте')
      else:
        posts = vk.wall.get(owner_id=vk_id, count=2)['items']
        if len(posts) > 1:
          last_id = posts[1]['id']
        else:
          last_id = 0
        users[user_id]['feeds'].update({domain:{'post_id':last_id, 'name':name, 'id':vk_id}})
        db.write('users', users)
        update.message.reply_text(f'Группа "{name}" добавлена в ленту')
    except vk_api.exceptions.ApiError as e:
      log.debug(f'Got {e} exception, handling...')
      if str(e)[:4] == '[15]':
        update.message.reply_text(f'Страница "{name}" приватная, добавить её в ленту нельзя')
        return
      try:
        domain = url.split('/')[-1]
        user = vk.users.get(user_ids=domain)
        vk_id = int(user[0]['id'])
        name = user[0]['first_name'] + ' ' + user[0]['last_name']
        if domain in users[user_id]['feeds']:
          update.message.reply_text(f'Пользователь "{name}" уже есть в ленте')
        else:
          posts = vk.wall.get(owner_id=vk_id, count=2)['items']
          if len(posts) > 1:
            last_id = posts[1]['id']
          else:
            last_id = 0
          users[user_id]['feeds'].update({domain:{'post_id':last_id, 'name':name, 'id':vk_id}})
          db.write('users', users)
          update.message.reply_text(f'Пользователь "{name}" добавлен в ленту')
      except vk_api.exceptions.ApiError as e:
        if str(e)[:4] == '[30]':
          update.message.reply_text(f'Страница "{name}" приватная, добавить её в ленту нельзя')
          return
        if str(e)[:5] == '[113]':
          update.message.reply_text(f'Такой страницы не существует')
          return
        log.debug(f'Got {e} exception, handling...')
    except ValueError:
      update.message.reply_text('Некорректная ссылка')
      help_command(update, context)

def show_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    users = db.read('users')
    if user_id not in users:
      add_user_to_db(user_id, update)
      users = db.read('users')
    if len(users[user_id]['feeds']) == 0:
      update.message.reply_text('Лента пуста')
    else:
      msg = 'Текущая лента:'
      i = 1
      for domain in users[user_id]['feeds']:
        name = users[user_id]['feeds'][domain]['name']
        msg += f'\n{i}: {name}\n#{domain}\nhttps://vk.com/{domain}'
        i += 1
      update.message.reply_text(msg)

def remove_from_feed(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    users = db.read('users')
    if user_id not in users:
      add_user_to_db(user_id, update)
      users = db.read('users')
    try:
      url = str(context.args[0])
      domain = url.split('/')[-1]
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

def get_inline_options_keyboard(options_dict, columns=2):
  keyboard = []
  for index in range(0, len(options_dict), columns):
    row = []
    for offset in range(columns):
      with suppress(IndexError):
        option_key = list(options_dict.keys())[index + offset]
        row.append(InlineKeyboardButton(option_key, callback_data=options_dict[option_key]))
    keyboard.append(row)
  return keyboard

def get_posts(update, context):
  if whitelisted(update.message.chat['id'], True):
    user_id = str(update.message.chat['id'])
    users = db.read('users')
    if user_id not in users:
      add_user_to_db(user_id, update)
      users = db.read('users')
    text, reply_markup = handle_posts_query(users, user_id)
    update.message.reply_text(text, reply_markup=reply_markup)

def handle_posts_query(users, user_id, query='0::'):
  page_entries = 5
  columns = 1
  page, chosen_feed, number_of_posts = query.split(':')
  page = int(page)
  if page < 0: page = 0
  if chosen_feed:
    chosen_feed_name = users[user_id]['feeds'][chosen_feed]['name']
    if number_of_posts:
      number_of_posts = int(number_of_posts)
      vk_id = users[user_id]['feeds'][chosen_feed]['id']
      log.info(f'Getting {number_of_posts} posts from {chosen_feed}')
      posts = vk.wall.get(owner_id=vk_id, count=number_of_posts)['items']
      posts.reverse()
      for post in posts:
        vk_posts.send_post(vk, tg, user_id, post, chosen_feed_name, chosen_feed, vk_id)
      text = f'Лента: {chosen_feed_name}\nКоличество постов: {number_of_posts}'
      return text, None
    else:
      options_dict = {}
      for number in range(1, 21):
        options_dict.update({number:f'posts|{page}:{chosen_feed}:{number}'})
      keyboard = get_inline_options_keyboard(options_dict, columns=4)
      reply_markup = InlineKeyboardMarkup(keyboard)
      text = f'Лента: {chosen_feed_name}\nКоличество постов?'
      return text, reply_markup
  else:
    options_dict = {}
    feed_slice_start = page * page_entries
    feed_slice_end = feed_slice_start + page_entries
    feed_page = list(users[user_id]['feeds'].keys())[feed_slice_start:feed_slice_end]
    for feed in feed_page:
      feed_name = users[user_id]['feeds'][feed]['name']
      options_dict.update({feed_name:f'posts|{page}:{feed}:{number_of_posts}'})
    keyboard = get_inline_options_keyboard(options_dict, columns)
    keyboard += [
        InlineKeyboardButton('<', callback_data=f'posts|{page-1}:{chosen_feed}:{number_of_posts}'),
        InlineKeyboardButton('>', callback_data=f'posts|{page+1}:{chosen_feed}:{number_of_posts}'),
        ],
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f'Лента для просмотра постов\nстр. {page+1}'
    return text, reply_markup

def callback_handler(update, context):
  users = db.read('users')
  query = update.callback_query
  user_id = str(query.message.chat_id)
  function, option = query.data.split('|')
  if function == 'posts':
    text, reply_markup = handle_posts_query(users, user_id, option)
  else:
    query.answer()
  with suppress(telegram.error.BadRequest):
    query.edit_message_text(text=text, reply_markup=reply_markup)
  query.answer()

def mainloop():
  try:
    while True:
      log.info('Started posts update...')
      users = db.read('users')
      params = db.read('params')
      for user in users.copy():
        username = users[user]['username']
        log.info(f'Checking posts for user @{username} {user}...')
        if whitelisted(int(user)):
          for domain in users.copy()[user]['feeds']:
            try:
              last_post_id = users[user]['feeds'][domain]['post_id']
              name = users[user]['feeds'][domain]['name']
              vk_id = users[user]['feeds'][domain]['id']
              log.info(f'Checking {name} ({domain})...')
              posts = vk.wall.get(owner_id=vk_id, count=50)['items']
              posts.reverse()
              for post in posts:
                if post['id'] > last_post_id and post['date'] > params['start_date']:
                  log.info(f'New post from {name} ({domain}) with id {post["id"]} for user @{users[user]["username"]} ({user})')
                  vk_posts.send_post(vk, tg, user, post, name, domain, vk_id)
                  last_post_id = post['id']
                  users[user]['feeds'][domain]['post_id'] = last_post_id
                  db.write('users', users)
            except vk_api.exceptions.ApiError as e:
              if str(e)[:4] == '[15]' or str(e)[:4] == '[30]':
                msg = f'Страница "{name}" приватная и не может быть в ленте\n'
                msg += f'/remove https://vk.com/{domain} чтобы удалить из ленты'
                tg.send_message(chat_id=user, text = msg)
      update_period = params['update_period']
      log.info('Finished posts update')
      log.info(f'Sleeping for {update_period} seconds...')
      time.sleep(update_period)
  except Exception as e:
    log.error(traceback.format_exc())
    admin_id = db.read('params')['admin']
    if admin_id:
      error_msg = f'VK Feed Bot stopped with an exception {e}'
      tg.send_message(chat_id=admin_id, text = error_msg, disable_notification=True)
      # tg.send_message(chat_id=admin_id, text = traceback.format_exc())
    return 0

if __name__ == '__main__':
  try:
    db.init('users')
    params = db.init('params')
    whitelist = db.init('whitelist')
    admin_id = params['admin']
    if admin_id:
      msg = f'VK Feed v{VERSION}\n'
      msg += f'Post start date: {params["start_date"]}\n'
      msg += f'Update period: {params["update_period"]} sec\n'
      if params['use_whitelist']:
        msg += f'Whitelist enabled, users:'
        for user in whitelist:
          msg += f'\n  {user}'
      else:
        msg += f'Whitelist disabled'
      tg.send_message(chat_id=admin_id, text = msg, disable_notification=True)
    updater = telegram.ext.Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, add_feed))
    dispatcher.add_handler(CommandHandler('help', help_command))
    dispatcher.add_handler(CommandHandler('start', start_command))
    dispatcher.add_handler(CommandHandler('feed', show_feed))
    dispatcher.add_handler(CommandHandler('remove', remove_from_feed))
    dispatcher.add_handler(CommandHandler('posts', get_posts))
    dispatcher.add_handler(CallbackQueryHandler(callback_handler))
    updater.start_polling()
    mainloop()
    log.error('Main thread ended, stopping updater...')
    updater.stop()
  except Exception as e:
    updater.stop()
    log.error((traceback.format_exc()))
