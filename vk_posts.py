import logging
import vk_api
from telegram import InputMediaPhoto, InputMediaDocument

log = logging.getLogger()

def get_photo(attachment):
  sizes = attachment['photo']['sizes']
  photo = sorted(sizes, key = lambda item: item['height'])[-1]
  return photo['url']

def get_doc(attachment):
  if attachment['doc']['ext'] == 'gif':
    return 'gif', attachment['doc']['url'],
  else:
    return 'doc', attachment['doc']['title'],

def get_video(attachment):
  return attachment['video']['title']

def get_audio(attachment):
  artist = attachment['audio']['artist']
  title = attachment['audio']['title']
  return f'{artist} - {title}'

def get_playlist(attachment):
  title = attachment['audio_playlist']['title']
  count = attachment['audio_playlist']['count']
  return f'{title} - {count} аудио'

def get_links(attachment, playlists, articles, links):
  if attachment['link']['description'] == 'Playlist':
    title = attachment['link']['title']
    url = attachment['link']['url']
    playlists.append(f'Музыкальный плейлист: {title}\n{url}')
  elif attachment['link']['description'] == 'Article':
    title = attachment['link']['title']
    url = attachment['link']['url']
    articles.append(f'Статья: {title}\n{url}')
  else:
    title = attachment['link']['title']
    url = attachment['link']['url']
    links.append(f'Ссылка: {title}\n{url}')
  return playlists, articles, links,

def get_sliced_messeges(text, bottom_text):
  messeges = []
  while True:
    if len(text) + len(bottom_text) + 3 >= 4096:
      messeges.append('...' + text[:4000] + '...')
      text = text[4000:]
    else:
      messeges.append('...' + text + bottom_text)
      break
  return messeges

def get_post(vk, post, poster_name, domain, feed_id):
  post_id = post['id']
  post_full = ''
  post_text = post['text']
  post_full += post_text
  if 'copy_history' in post.keys():
    try:
      group = vk.groups.getById(group_id=post['copy_history'][0]['from_id'] * -1)
      name = group[0]['name']
    except vk_api.exceptions.ApiError as e:
      log.debug(f'Got {e} exception, handling...')
      user = vk.users.get(user_ids=post['copy_history'][0]['from_id'])
      name = user[0]['first_name'] + ' ' + user[0]['last_name']
    post_full += f'\n------------------------\nРепост со страницы {name}\n'
    post = post['copy_history'][0]
    post_full += post['text']
  post_size_warning = '...\n* Пост слишком большой для Telegram *'
  post_bottom_text = f'\n------------------------\n{poster_name}\nhttps://vk.com/wall{feed_id}_{post_id}'
  post_photos = []
  post_videos = []
  post_audios = []
  post_playlists = []
  post_articles = []
  post_links = []
  post_gifs = []
  post_docs = []
  post_long_text = []
  if 'attachments' in post.keys():
    attachments = post['attachments']
    for attachment in attachments:
      if attachment['type'] == 'photo':
        post_photos.append(get_photo(attachment))
      elif attachment['type'] == 'video':
        post_videos.append(get_video(attachment))
      elif attachment['type'] == 'audio':
        post_audios.append(get_audio(attachment))
      elif attachment['type'] == 'audio_playlist':
        post_playlists.append(get_playlist(attachment))
      elif attachment['type'] == 'link':
        post_playlists, post_articles, post_links = get_links(attachment,
                                                            post_playlists,
                                                            post_articles,
                                                            post_links
                                                            )
      elif attachment['type'] == 'doc':
        doc = get_doc(attachment)
        if doc[0] == 'gif':
          post_gifs.append(doc[1])
        else:
          post_docs.append(doc[1])
  gif_count = len(post_gifs)
  if len(post_photos) != 0 and len(post_gifs) != 0:
    post_gifs = []
    post_full += '\n' + f'В посте ещё {gif_count} gif'
  if len(post_gifs) > 1:
    post_gifs = [post_gifs[0]]
    post_full += '\n' + f'В посте ещё {gif_count-1} gif'
  for video in post_videos:
    post_full += f'\nВидео: {video}'
  for audio in post_audios:
    post_full += f'\nАудио: {audio}'
  for playlist in post_playlists:
    post_full += '\n' + playlist
  for article in post_articles:
    post_full += '\n' + article
  for link in post_links:
    post_full += '\n' + link
  for doc in post_docs:
    post_full += f'\nДокумент: {doc}'
  post_msg = post_full + post_bottom_text
  msg_size = len(post_full + post_bottom_text)
  if msg_size > 1024 and ( post_photos or post_gifs ):
    post_msg = post_full[:1000] +  '...'
    post_long_text = get_sliced_messeges(post_full[1000:], post_bottom_text)
  if msg_size > 4096 and not post_photos and not post_gifs:
    post_msg = post_full[:4000] + '...'
    post_long_text = get_sliced_messeges(post_full[4000:], post_bottom_text)
  return {'text':post_msg, 'photos':post_photos, 'gifs':post_gifs, 'long_text':post_long_text}

def send_post(vk, tg, user_id, post, poster_name, domain, feed_id):
  msg = get_post(vk, post, poster_name, domain, feed_id)
  msg_media = []
  if len(msg['gifs']) == 1:
    tg.send_document(chat_id=user_id, document=msg['gifs'][0], caption=msg['text'])
  if len(msg['photos']) > 1:
    for photo in msg['photos']:
      if photo is msg['photos'][0]:
        msg_media.append(InputMediaPhoto(media=photo, caption=msg['text']))
      else:
        msg_media.append(InputMediaPhoto(media=photo))
    tg.sendMediaGroup(chat_id=user_id, media=msg_media)
  if len(msg['photos']) == 1:
    tg.send_photo(chat_id=user_id, photo=msg['photos'][0], caption=msg['text'])
  if not msg['photos'] and not msg['gifs']:
    tg.send_message(chat_id=user_id, text=msg['text'])
  for long_text in msg['long_text']:
    tg.send_message(chat_id=user_id, text=long_text)
