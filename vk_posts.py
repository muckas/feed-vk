import logging
import telegram

log = logging.getLogger()

def send(tg, user_id, post, poster_name, domain, feed_id, post_id):
  msg_text = ''
  msg_attachments = []
  post_id = post['id']
  msg_text = post['text']
  if 'attachments' in post.keys():
    attachments = post['attachments']
    for attachment in attachments:
      if attachment['type'] == 'photo':
        sizes = attachment['photo']['sizes']
        photo = sorted(sizes, key = lambda item: item['height'])[-1]
        msg_attachments.append(photo['url'])
  if len(msg_attachments) > 1:
    if len(msg_text) > 1024:
      msg_text = msg_text[:800] 
      msg_text += '...\n* В посте слишком много текста для отправки в Telegram *'
    msg_text += '\n----------------------------\n' + poster_name + f'\nhttps://vk.com/wall{feed_id}_{post_id}'
    msg_photos = []
    for photo in msg_attachments:
      if photo is msg_attachments[0]:
        msg_photos.append(telegram.InputMediaPhoto(media=photo, caption=msg_text))
      else:
        msg_photos.append(telegram.InputMediaPhoto(media=photo))
    tg.sendMediaGroup(chat_id=user_id, media=msg_photos)
  elif len(msg_attachments) == 1:
    if len(msg_text) > 1024:
      msg_text = msg_text[:900] 
      msg_text += '...\n* В посте слишком много текста для отправки в Telegram *'
    msg_text += '\n----------------------------\n' + poster_name + f'\nhttps://vk.com/wall{feed_id}_{post_id}'
    tg.send_photo(chat_id=user_id, photo=msg_attachments[0], caption=msg_text)
  else:
    if len(msg_text) > 4096:
      msg_text = msg_text[:900] + '...\n* В посте слишком много текста для отправки в Telegram *'
    msg_text += '\n----------------------------\n' + poster_name + f'\nhttps://vk.com/wall{feed_id}_{post_id}'
    tg.send_message(chat_id=user_id, text=msg_text)
