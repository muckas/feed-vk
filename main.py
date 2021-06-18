import os
import vk_api

login = os.environ['VK_LOGIN']
password = os.environ['VK_PASSWORD']

vk_session = vk_api.VkApi(login , password)
vk_session.auth()
vk = vk_session.get_api()

posts = vk.wall.get(domain='fest', count=20)['items']

for post in posts:
  msg_text = ''
  msg_attachments = ''
  post_id = post['id']
  post_text = post['text']
  msg_text = post_text
  if 'attachments' in post.keys():
    attachments = post['attachments']
    for attachment in attachments:
      if attachment['type'] == 'photo':
        msg_attachments += 'photo\n'
  print(msg_text + '\n' + msg_attachments)
