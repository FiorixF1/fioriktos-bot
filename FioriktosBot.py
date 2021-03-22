from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from os import environ, getpid
from functools import wraps
from hashlib import md5
import datetime
import psycopg2
import logging
import psutil
import random
import boto3
import time
import json

# Enable log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)



""" Environment variables """
BOT_TOKEN             = environ.get("BOT_TOKEN")
ADMIN                 = int(environ.get("ADMIN"))
HEROKU_APP_NAME       = environ.get("HEROKU_APP_NAME")
DATABASE_URL          = environ.get("DATABASE_URL")
PORT                  = int(environ.get("PORT", "8443"))
AWS_ACCESS_KEY_ID     = environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
REGION_NAME           = environ.get("REGION_NAME")
S3_BUCKET_NAME        = environ.get("S3_BUCKET_NAME")



""" Constants """
BEGIN = ""
END = 0
ENDING_PUNCTUATION_MARKS = ".!?\n"
MESSAGE = "Message"
STICKER = "Sticker"
ANIMATION = "Animation"

GDPR = "To work correctly, I need to store these information for each chat:" + \
       "\n- Chat ID" + \
       "\n- Sent words" + \
       "\n- Sent stickers" + \
       "\n- Sent gifs" + \
       "\nI don't store any information about users, such as user ID, username, profile picture..." + \
       "\nData are automatically deleted after 90 days of inactivity." + \
       "\nFor more information, you can visit https://www.github.com/FiorixF1/fioriktos-bot.git or contact my developer @FiorixF1."

WELCOME = "Hi! I am Fioriktos and I can learn how to speak! You can interact with me using the following commands:" + \
          "\n- /fioriktos : Let me generate a message" + \
          "\n- /sticker : Let me send a sticker" + \
          "\n- /gif : Let me send a gif" + \
          "\n- /torrent n : Let me reply automatically to messages sent by others. The parameter n sets how much talkative I am and it must be a number between 0 and 10: with /torrent 10 I will answer all messages, while /torrent 0 will mute me. If you want to know my current parameter, send /torrent?" + \
          "\n- You can enable or disable my learning ability with the commands /enablelearning and /disablelearning" + \
          "\n- /thanos : This command will delete half the memory of the chat. Use it wisely!" + \
          "\n- /bof : If I say something funny, you can make a screenshot and send it with this command in the description. Your screenshot could get published on @BestOfFioriktos" + \
          "\n- /gdpr : Here you can have more info about privacy and visit my source code 💻"



""" Global state variables """
CHATS = dict()          # key = chat_id --- value = object Chat
BLOCKED_CHATS = []
LAST_SYNC = time.time() # for automatic serialization on database



""" Data structures """
class Chat:
    def __init__(self):
        self.torrent_level = 5
        self.is_learning = True
        self.model = { BEGIN: [END] }
        self.stickers = []
        self.animations = []
        self.last_update = time.time()

    def learn_text(self, text):
        if self.is_learning:
            for sentence in text.split('\n'):
                # pre-processing and filtering
                tokens = sentence.split()
                tokens = [BEGIN] + list(filter(lambda x: "http" not in x, tokens)) + [END]

                # actual learning
                for i in range(len(tokens)-1):
                    token = tokens[i]
                    successor = tokens[i+1]

                    # use the token without special characters
                    filtered_token = self.filter(token)
                    if filtered_token != token:
                        self.model[token] = list()
                        token = filtered_token

                    if token not in self.model:
                        self.model[token] = list()

                    if len(self.model[token]) < 256:
                        self.model[token].append(successor)
                    else:
                        guess = random.randint(0, 255)
                        self.model[token][guess] = successor

    def learn_sticker(self, sticker):
        if self.is_learning:
            if len(self.stickers) < 1024:
                self.stickers.append(sticker)
            else:
                guess = random.randint(0, 1023)
                self.stickers[guess] = sticker

    def learn_animation(self, animation):
        if self.is_learning:
            if len(self.animations) < 1024:
                self.animations.append(animation)
            else:
                guess = random.randint(0, 1023)
                self.animations[guess] = animation
        if animation == "CgADBAADcwMAAsNFiVKRKWfct4l-jxYE":
            self.torrent_level = 0

    def reply(self):
        if random.random()*10 < self.torrent_level**2/10:
            if random.random()*10 < 9.5:
                return (MESSAGE, self.talk())
            else:
                type_of_reply = random.choice([STICKER, ANIMATION])
                if type_of_reply == STICKER:
                    return (STICKER, self.choose_sticker())
                elif type_of_reply == ANIMATION:
                    return (ANIMATION, self.choose_animation())
        return ""

    def talk(self):
        walker = BEGIN if random.random() < 0.5 else random.choice(list(self.model.keys()))
        answer = [walker]
        while True:
            filtered_walker = self.filter(walker)
            if filtered_walker != walker:
                walker = filtered_walker
            new_token = random.choice(self.model[walker])
            # avoid empty messages with non empty model
            if new_token == END and len(answer) == 1 and len(set(self.model[BEGIN])) > 1:
                while new_token == END:
                    new_token = random.choice(self.model[BEGIN])
            if new_token == END:
                break
            answer.append(new_token)
            walker = new_token
        return ' '.join(answer)

    def choose_sticker(self):
        try:
            return random.choice(self.stickers)
        except:
            return ""

    def choose_animation(self):
        try:
            return random.choice(self.animations)
        except:
            return ""

    def set_torrent(self, new_level):
        if new_level >= 0 and new_level <= 10:
            self.torrent_level = new_level

    def get_torrent(self):
        return self.torrent_level

    def enable_learning(self):
        self.is_learning = True

    def disable_learning(self):
        self.is_learning = False

    def halve(self):
        for word in self.model:
            length = len(self.model[word])
            if length != 0:
                self.model[word] = self.model[word][length//2:] + [END]
        length = len(self.stickers)
        self.stickers = self.stickers[length//2:]
        length = len(self.animations)
        self.animations = self.animations[length//2:]

    def clean(self):
        # find words that are not referenced by any other word: those can be deleted safely
        words = set(self.model.keys())
        referenced_words = { BEGIN }
        for word in words:
            for successor in self.model[word]:
                referenced_words.add(successor)
                referenced_words.add(self.filter(successor))
        to_remove = words - referenced_words
        del words, referenced_words
        # there are many unreferenced words: among them, we delete only those with no successors except for END
        not_to_remove = set()
        for word in to_remove:
            successors = set(self.model[word]) - { END }
            if len(successors) != 0:
                not_to_remove.add(word)
                not_to_remove.add(self.filter(word))
        to_remove = to_remove - not_to_remove
        del not_to_remove
        # delete lonely words
        for word in to_remove:
            del self.model[word]
        del to_remove

    def filter(self, word):
        if type(word) != type(''):
            return word
        return ''.join(filter(lambda ch: ch.isalnum(), word)).lower()

    def __str__(self):
        jsonification = {"torrent_level": self.torrent_level,
                         "is_learning": self.is_learning,
                         "model": self.model,
                         "stickers": self.stickers,
                         "animations": self.animations,
                         "last_update": self.last_update}
        return json.dumps(jsonification)



""" Decorators """
def restricted(f):
    @wraps(f)
    def wrapped(bot, update, *args, **kwargs):
        user_id = update.effective_user.id
        username = update.effective_user.username
        if user_id != ADMIN:
            print("Unauthorized access denied for {} ({}).".format(user_id, username))
            return
        f(bot, update, *args, **kwargs)
    return wrapped

def chat_finder(f):
    @wraps(f)
    def wrapped(bot, update, *args, **kwargs):
        chat_id = update.message.chat_id
        try:
            chat = CHATS[chat_id]
        except:
            chat = Chat()
            CHATS[chat_id] = chat
        chat.last_update = time.time()
        if chat_id in BLOCKED_CHATS:
            if update.message.text.startswith('/'):
                bot.send_message(chat_id=chat_id, text="NAK // SCIOPERO")
            return
        f(bot, update, chat, *args, **kwargs)
    return wrapped

def serializer(f):
    @wraps(f)
    def wrapped(bot, update, *args, **kwargs):
        global LAST_SYNC

        f(bot, update, *args, **kwargs)

        now = time.time()
        if now - LAST_SYNC > 666:  # 37% rule
            delete_old_chats()
            thanos_big_chats()
            store_db()
            send_report()
            LAST_SYNC = now

    return wrapped



""" Commands """
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="SYN")

@serializer
@chat_finder
def fioriktos(bot, update, chat):
    reply = chat.talk()
    if reply != "":
        bot.send_message(chat_id=update.message.chat_id, text=reply)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty chain")

@serializer
@chat_finder
def choose_sticker(bot, update, chat):
    reply = chat.choose_sticker()
    if reply != "":
        bot.send_sticker(chat_id=update.message.chat_id, sticker=reply)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty sticker set")

@serializer
@chat_finder
def choose_animation(bot, update, chat):
    reply = chat.choose_animation()
    if reply != "":
        bot.send_animation(chat_id=update.message.chat_id, animation=reply)
    else:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty gif set")

@serializer
@chat_finder
def torrent(bot, update, chat, args):
    try:
        quantity = int(args[0])
        if quantity < 0 or quantity > 10:
            bot.send_message(chat_id=update.message.chat_id, text="NAK // Send /torrent with a number between 0 and 10.")
        else:
            chat.set_torrent(quantity)
            bot.send_message(chat_id=update.message.chat_id, text="ACK")
    except:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Send /torrent with a number between 0 and 10.")

@serializer
@chat_finder
def torrent_question_mark(bot, update, chat):
    bot.send_message(chat_id=update.message.chat_id, text=str(chat.get_torrent()))

@serializer
@chat_finder
def enable_learning(bot, update, chat):
    chat.enable_learning()
    bot.send_message(chat_id=update.message.chat_id, text="Learning enabled")

@serializer
@chat_finder
def disable_learning(bot, update, chat):
    chat.disable_learning()
    bot.send_message(chat_id=update.message.chat_id, text="Learning disabled")

@serializer
@chat_finder
def thanos(bot, update, chat, args):
    try:
        expected = md5(str(update.message.chat_id).encode()).hexdigest().upper()
        real = args[0]
        if real != expected:
            bot.send_message(chat_id=update.message.chat_id, text="NAK // Send this message to delete half the memory of this chat.")
            bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))
        else:
            bot.send_message(chat_id=update.message.chat_id, text="ACK // Currently this chat has {} words, {} stickers and {} gifs for a total size of {} bytes. Let's do some cleaning.".format(len(chat.model),
                                                                                                                                                                                                  len(chat.stickers),
                                                                                                                                                                                                  len(chat.animations),
                                                                                                                                                                                                  len(str(chat).encode())))
            time.sleep(6)
            bot.send_animation(chat_id=update.message.chat_id, animation=open('thanos.mp4', 'rb'))            
            
            # destroy half the chat
            chat.halve()
            # delete isolated words
            chat.clean()
            
            time.sleep(6)
            bot.send_message(chat_id=update.message.chat_id, text="Now this chat contains {} words, {} stickers and {} gifs for a total size of {} bytes.".format(len(chat.model),
                                                                                                                                                                  len(chat.stickers),
                                                                                                                                                                  len(chat.animations),
                                                                                                                                                                  len(str(chat).encode())))
    except:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Send this message to delete half the memory of this chat.")
        bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))

@serializer
@chat_finder
def bof(bot, update, chat):
    if not update.message.photo:
        bot.send_message(chat_id=update.message.chat_id, text="NAK // Send a screenshot with /bof in the description, you could get published on @BestOfFioriktos")
    elif update.message.caption and ("/bof" in update.message.caption or "/bestoffioriktos" in update.message.caption):
        bot.send_photo(chat_id=ADMIN, photo=update.message.photo[-1])
        bot.send_message(chat_id=update.message.chat_id, text="ACK")

@serializer
@chat_finder
def learn_text_and_reply(bot, update, chat):
    chat.learn_text(update.message.text)
    reply(bot, update, chat)

@serializer
@chat_finder
def learn_sticker_and_reply(bot, update, chat):
    chat.learn_sticker(update.message.sticker.file_id)
    reply(bot, update, chat)

@serializer
@chat_finder
def learn_animation_and_reply(bot, update, chat):
    chat.learn_animation(update.message.animation.file_id)
    reply(bot, update, chat)

@serializer
@chat_finder
def gdpr(bot, update, chat):
    bot.send_message(chat_id=update.message.chat_id, text=GDPR)

@serializer
@chat_finder
def welcome(bot, update, chat):
    # send welcome message only when added to new chat
    if len(chat.model) == 1:
        for member in update.message.new_chat_members:
            if member.username == 'FioriktosBot':
                bot.send_message(chat_id=update.message.chat_id, text=WELCOME)

def reply(bot, update, chat):
    response = chat.reply()

    if len(response) == 2:
        type_of_response = response[0]
        content = response[1]

        if content != "":
            if type_of_response == MESSAGE:
                bot.send_message(chat_id=update.message.chat_id, text=content)
            elif type_of_response == STICKER:
                bot.send_sticker(chat_id=update.message.chat_id, sticker=content)
            elif type_of_response == ANIMATION:
                bot.send_animation(chat_id=update.message.chat_id, animation=content)
        else:
            bot.send_message(chat_id=update.message.chat_id, text="NAK")

def load_db():
    s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
    dump = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key="dump.txt")
    data = dump['Body'].read()
    unjsonify(data)
    return data

def store_db():
    data = jsonify()
    s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
    s3_client.put_object(Body=data.encode(), Bucket=S3_BUCKET_NAME, Key="dump.txt")
    return data

def jsonify():
    jsonification = dict()
    for chat_id in CHATS:
        jsonification[chat_id] = str(CHATS[chat_id])
    data = json.dumps(jsonification, indent=2)
    return data

def unjsonify(data):
    chats_tmp = json.loads(data)

    for chat_id in chats_tmp:
        jsonized_chat = json.loads(chats_tmp[chat_id])

        deserialized_chat = Chat()
        deserialized_chat.torrent_level = jsonized_chat["torrent_level"]
        deserialized_chat.is_learning = jsonized_chat["is_learning"]
        deserialized_chat.model = jsonized_chat["model"]
        deserialized_chat.stickers = jsonized_chat["stickers"]
        deserialized_chat.animations = jsonized_chat["animations"]
        deserialized_chat.last_update = jsonized_chat["last_update"]

        CHATS[int(chat_id)] = deserialized_chat

def delete_old_chats():
    now = time.time()
    for chat_id in list(CHATS.keys()):
        if now - CHATS[chat_id].last_update > 7776000:
            del CHATS[chat_id]

def thanos_big_chats():
    for chat_id in list(CHATS.keys()):
        if len(CHATS[chat_id].model) > 50000:
            CHATS[chat_id].halve()
            CHATS[chat_id].clean()

def send_report():
    # each day send me automatically a report of used resources so I do not need to check manually on Heroku :)
    today = datetime.datetime.now()
    try:
        if today.hour == 23 and today.minute >= 50:
            header = "[DAILY REPORT]"
            ram_report = f"{psutil.Process(getpid()).memory_info().rss / 1024 ** 2} / 1024 MB used"
            chats_report = f"{len(CHATS)} chats"
            telemetry = [header, ram_report, chats_report]
            bot.send_message(chat_id=ADMIN, text="\n".join(telemetry))
    except Exception as ex:
        bot.send_message(chat_id=ADMIN, text=str(ex))

def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



def main():
    """Start the bot"""

    # Restore data
    load_db()

    # Create the EventHandler and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("fioriktos", fioriktos))
    dp.add_handler(CommandHandler("sticker", choose_sticker))
    dp.add_handler(CommandHandler("gif", choose_animation))
    dp.add_handler(CommandHandler("torrent", torrent, pass_args=True))
    dp.add_handler(CommandHandler("torrent?", torrent_question_mark))
    dp.add_handler(CommandHandler("enablelearning", enable_learning))
    dp.add_handler(CommandHandler("disablelearning", disable_learning))
    dp.add_handler(CommandHandler("thanos", thanos, pass_args=True))
    dp.add_handler(CommandHandler("bof", bof))
    dp.add_handler(CommandHandler("bestoffioriktos", bof))
    dp.add_handler(CommandHandler("gdpr", gdpr))

    # on noncommand i.e. message
    dp.add_handler(MessageHandler(Filters.text, learn_text_and_reply))
    dp.add_handler(MessageHandler(Filters.sticker, learn_sticker_and_reply))
    dp.add_handler(MessageHandler(Filters.animation, learn_animation_and_reply))
    dp.add_handler(MessageHandler(Filters.photo, bof))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    
    # log all errors
    dp.add_error_handler(error)

    # start the Bot
    #updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    #updater.idle()

    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=BOT_TOKEN)
    updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, BOT_TOKEN))

if __name__ == '__main__':
    main()
