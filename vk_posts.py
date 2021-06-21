import logging

log = logging.getLogger()

def send(tg, user_id, post, poster_name, domain, feed_id):
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
    if len(msg_text) > 1024:
      msg_text = msg_text[:-100] + '...\n* В посте слишком много текста для отправки в Telegram *'
    msg_photos = []
    for photo in msg_attachments:
      if photo is msg_attachments[0]:
        msg_photos.append(telegram.InputMediaPhoto(media=photo, caption=msg_text))
      else:
        msg_photos.append(telegram.InputMediaPhoto(media=photo))
    tg.sendMediaGroup(chat_id=user_id, media=msg_photos)
  elif len(msg_attachments) == 1:
    if len(msg_text) > 1024:
      msg_text = msg_text[:-100] + '...\n* В посте слишком много текста для отправки в Telegram *'
    tg.send_photo(chat_id=user_id, photo=msg_attachments[0], caption=msg_text)
  else:
    if len(msg_text) > 4096:
      msg_text = msg_text[:-100] + '...\n* В посте слишком много текста для отправки в Telegram *'
    tg.send_message(chat_id=user_id, text=msg_text)
