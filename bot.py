#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Exit codes of functions addSubscriber() and delSubscriber():
# 0 - well done
# 1 - something goes wrong
# 3 - no such user
# 4 - user is already in database

import telegram, configparser, logging, os, sys, re
from threading import Thread
from time import sleep
from bs4 import BeautifulSoup
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen                          # python 3.4.3 (raspbian)
try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError                                # python 2
try:
    sys.path.append('.private'); from config import TOKEN       # importing secret TOKEN
except ImportError:
    print("need TOKEN from .private/config.py")
    sys.exit(1)
user_db = "user_db"
news = "last_news"
TIMEOUT = 30
URL = "http://vandrouki.ru"
log_file = "bot.log"


def main():
  logging.basicConfig(
      level = logging.WARNING,
      filename=log_file,
      format='%(asctime)s:%(levelname)s - %(message)s')
  
  for file in news, user_db:
      if not os.path.exists(file):
          open(file, 'w').close()
          logging.warning('file %s created' % file)
  open(log_file, 'w').close()
          
  bot = telegram.Bot(TOKEN)
  logging.warning('bot started...')
  try:
      update_id = bot.getUpdates()[0].update_id
  except IndexError:
      update_id = None

  def notificateUser():
    while True:
      if getLastNews() == 0:
          with open(user_db,'r') as file:
              for user in file.read().splitlines():
                if user.strip() == '':                                                       # don`t touch empty lines
                  pass
                else:
                  bot.sendMessage(chat_id=user,
                          text=open(news, 'r').read())
                  logging.warning('user %s is notified' % user)
      sleep(TIMEOUT)

  def getLastNews(): 
    global news
    try:
        soup = BeautifulSoup(urlopen(URL), "html.parser")
        with open(news, 'r') as file:
          for a in soup.findAll('a', { 'rel': 'bookmark' }):
#              new_message = "%s (%s)" % (a.get_text(), str(a.get('href')))
              new_message = str(a.get('href'))
#              if new_message.encode('utf-8') == file.readline():                           # RASPBIAN PROBLEM
              if new_message == file.readline():                                            # file and variable are the same, so no news
                pass
                return 1
              else:
                with open(news, 'w') as file:
                  try:
                      file.write(new_message.encode('utf-8')) # python 3.4.3 raspbian
                  except TypeError:
                      file.write(new_message)
                logging.warning('new message! news updated')
                return 0
    except Exception:
        logging.error('some problems with getLastNews()')
        return 1

  bot = telegram.Bot(TOKEN)
  try:
      update_id = bot.getUpdates()[0].update_id
  except IndexError:
      update_id = None
  
  t = Thread(target=notificateUser)
  t.daemon = True
  t.start()
  
  while True:
      try:
          update_id = echo(bot, update_id)
      except telegram.TelegramError as e:
          # These are network problems with Telegram.
          if e.message in ("Bad Gateway", "Timed out"):
              sleep(1)
          elif e.message == "Unauthorized":
              # The user has removed or blocked the bot.
              update_id += 1
          else:
              raise e
      except URLError as e:
          # These are network problems on our end.
          sleep(1)

def addSubscriber(chat_id):
  try:
    if os.path.exists(user_db):
      with open(user_db,'r') as file:
        if str(chat_id) in file.read().splitlines():
          logging.warning('user %s already in database' % chat_id)
          return 4
          pass
        else:
          with open(user_db,'a') as file:
            file.write(str(chat_id) + '\n')
          logging.warning('added %s' % chat_id)
          return 0
    else:                                                                       # db does not exist
      with open(user_db,'w') as file:
        file.write(str(chat_id) + '\n')
      logging.warning('DB created! added %s' % chat_id)
      return 0
  except Exception:
    logging.error('addSubscriber(): some problems with %s while' % chat_id)
    return 1
  
def delSubscriber(chat_id):
  try:
    if os.path.exists(user_db):
      users = open(user_db).read()
      if str(chat_id) in users:                                                 # if chat_id in user_db,..
        new_user_db = open(user_db,"w")
        new_user_db.write(re.sub(str(chat_id) + '\n','', users))                # ..so delete it
        new_user_db.close()
        logging.warning('%s is deleted' % chat_id)
        return 0
      else:
        logging.warning('no such user: %s' % chat_id)
        pass
        return 3
    else:                                                                       # db does not exist
      new_user_db = open(user_db,"w")
      new_user_db.close()
      logging.warning('no such user: %s' % chat_id)
      return 3
  except Exception:
    logging.error('delSubscriber(): some problems with %s' % chat_id)
    return 1
  
def echo(bot, update_id):                                                       # Request updates after the last update_id
    for update in bot.getUpdates(offset=update_id, timeout=10):                 # chat_id is required to reply to any message
        chat_id = update.message.chat_id
        update_id = update.update_id + 1
        message = update.message.text

        if message == "/start":                                                 # Reply to the start message
            if addSubscriber(chat_id) == 0:
              bot.sendMessage(chat_id=chat_id,
                            text="Привет! Вы подписаны на обновления vandrouki. Ожидайте новостей, а вот из последнего: %s" % open(news, 'r').readline())
            elif addSubscriber(chat_id) == 4:
              bot.sendMessage(chat_id=chat_id,
                            text="Вы ведь уже подписаны на обновления vandrouki!")
            else:
              bot.sendMessage(chat_id=chat_id,
                            text="У нас что-то пошло не так...")
        elif message == "/stop":                                                # Reply to the message
            if delSubscriber(chat_id) == 0:
              bot.sendMessage(chat_id=chat_id,
                              text="Вы отписались от обновления vandrouki. Пока!")
            elif delSubscriber(chat_id) == 3:
              bot.sendMessage(chat_id=chat_id,
                              text="Привет! А Вы не подписаны на обновления vandrouki.")
            else:
              bot.sendMessage(chat_id=chat_id,
                              text="У нас что-то пошло не так...")
        elif message:
          bot.sendMessage(chat_id=chat_id,
                              text="Что-что? Я понимаю только /start и /stop")
    return update_id

if __name__ == '__main__':
    main()
