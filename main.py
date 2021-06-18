import os
import datetime
import vk_api
import telegram
import logging
from contextlib import suppress
import db

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
tg_token = os.environ['TG_TOKEN_TEST']
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

if __name__ == '__main__':
  settings = db.init()
  print(settings)
  db.write(settings)
