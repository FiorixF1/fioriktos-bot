from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from functools import wraps
from os import environ
import psycopg2
import logging
import random
import json

# Abilita log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)



""" Costanti """
BOT_TOKEN = environ.get("BOT_TOKEN")
DATABASE_URL = environ['DATABASE_URL']
HEROKU_APP_NAME = "fioriktos"
PORT = int(environ.get("PORT", "8443"))

END = 0
PUNCTUATION_MARKS = ".!?\n"
MESSAGE = "Message"
STICKER = "Sticker"
ANIMATION = "Animation"



""" Variabili di stato globali """
FIORIXF1 = 289439604
ADMINS = [FIORIXF1]
ADMINS_USERNAME = { FIORIXF1: "FiorixF1",
                  }
CHATS = dict()      # key = chat_id --- value = object Chat
REQUEST_COUNTER = 0 # for automatic serialization on database



""" Strutture dati """
class Chat:
    def __init__(self):
        self.torrent_level = 0
        self.is_learning = True
        self.model = { "...":  [END] }
        self.stickers = []
        self.animations = []

    def learn_text(self, text):
        if self.is_learning:
            # pre-processing
            text = text.replace('\n', '. ')

            # actual learning
            tokens = text.lower().split() + [END]
            for i in range(len(tokens)-1):
                token = tokens[i]
                successor = tokens[i+1]

                if token not in self.model:
                    self.model[token] = list()

                if len(self.model[token]) < 200:
                    self.model[token].append(successor)
                else:
                    guess = random.randint(0, 199)
                    self.model[token][guess] = successor

                if type(token) == type("A") and token[-1] in PUNCTUATION_MARKS:
                    if len(self.model[token]) < 200:
                        self.model[token].append(END)
                    else:
                        guess = random.randint(0, 199)
                        self.model[token][guess] = END

    def learn_sticker(self, sticker):
        if len(self.stickers) < 500:
            self.stickers.append(sticker)
        else:
            guess = random.randint(0, 499)
            self.stickers[guess] = sticker

    def learn_animation(self, animation):
        if len(self.animations) < 500:
            self.animations.append(animation)
        else:
            guess = random.randint(0, 499)
            self.animations[guess] = animation

    def reply(self):
        if random.random()*10 < self.torrent_level:
            if random.random()*10 < 9.5:
                return (MESSAGE, self.talk())
            else:
                type_of_reply = random.choice([STICKER, ANIMATION])
                if type_of_reply == STICKER:
                    return (STICKER, random.choice(self.stickers))
                elif type_of_reply == ANIMATION:
                    return (ANIMATION, random.choice(self.animations))
        return ""

    def talk(self):
        walker = random.choice(list(self.model.keys()))
        answer = [walker]
        while True:
            new_token = random.choice(self.model[walker])
            if new_token == END:
                break
            answer.append(new_token)
            walker = new_token
        return ' '.join(answer)

    def set_torrent(self, new_level):
        if new_level >= 0 and new_level <= 10:
            self.torrent_level = new_level

    def enable_learning(self):
        self.is_learning = True

    def disable_learning(self):
        self.is_learning = False

    def __str__(self):
        jsonification = {"torrent_level": self.torrent_level,
                         "is_learning": self.is_learning,
                         "model": self.model,
                         "stickers": self.stickers,
                         "animations": self.animations}
        return json.dumps(jsonification, indent=4)



""" Decoratori """
def restricted(f):
    @wraps(f)
    def wrapped(bot, update, *args, **kwargs):
        id = update.effective_user.id
        username = update.effective_user.username
        if id not in ADMINS:
            print("Unauthorized access denied for {} ({}).".format(id, username))
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
        f(bot, update, chat, *args, **kwargs)
    return wrapped

def serializer(f):
    @wraps(f)
    def wrapped(bot, update, *args, **kwargs):
        global REQUEST_COUNTER
    
        f(bot, update, *args, **kwargs)
        
        REQUEST_COUNTER += 1
        if REQUEST_COUNTER % 100 == 0:
            data = jsonify()
            
            # delete everything
            connection = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = connection.cursor()
            cursor.execute("DELETE FROM fioriktos;")
            connection.commit()
            cursor.close()
            connection.close()
            
            # add newer data
            data = [data[i:i+65536] for i in range(0, len(data), 65536)]
            
            connection = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = connection.cursor()
            for i in len(data):
                cursor.execute("INSERT INTO fioriktos VALUES (%d, %s)", (i, data[i]))
            connection.commit()
            cursor.close()
            connection.close()
            
    return wrapped



""" Comandi """
@serializer
@chat_finder
def fioriktos(bot, update, chat):
    reply = chat.talk()
    bot.send_message(chat_id=update.message.chat_id, text=reply)

@serializer
@chat_finder
def torrent(bot, update, chat, args):
    try:
        quantity = int(args[0])
        if quantity < 0 or quantity > 10:
            bot.send_message(chat_id=update.message.chat_id, text="Send /torrent with a number between 0 and 10.")
        else:
            chat.torrent_level = quantity
            bot.send_message(chat_id=update.message.chat_id, text="ACK")
    except:
        bot.send_message(chat_id=update.message.chat_id, text="Send /torrent with a number between 0 and 10.")

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

@chat_finder
def debug(bot, update, chat):
    print(chat)

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

def reply(bot, update, chat):
    response = chat.reply()

    if len(response) == 2:
        type_of_response = response[0]
        content = response[1]

        if type_of_response == MESSAGE and content != "":
            bot.send_message(chat_id=update.message.chat_id, text=content)
        elif type_of_response == STICKER:
            bot.send_sticker(chat_id=update.message.chat_id, sticker=content)
        elif type_of_response == ANIMATION:
            bot.send_animation(chat_id=update.message.chat_id, animation=content)

# by file
def serialize(bot, update):
    if update.effective_user.id in ADMINS:
        data = jsonify()
        with open("dump.txt", "w") as dump:
            dump.write(data)
        bot.send_document(chat_id=update.message.chat_id, document=open("dump.txt", 'rb'))

# by file
def deserialize(bot, update):
    if update.effective_user.id in ADMINS and update.message.document.mime_type == "text/plain":
        try:
            file_id = update.message.document.file_id
            bot.get_file(file_id).download('dump.txt')

            with open("dump.txt", "r") as dump:
                data = dump.read()
            unjsonify(data)

            bot.send_message(chat_id=update.message.chat_id, text="ACK")
        except Exception as e:
            bot.send_message(chat_id=update.message.chat_id, text="NAK")
            print(e)

def jsonify():
    jsonification = dict()
    for chat_id in CHATS:
        jsonification[chat_id] = str(CHATS[chat_id])
    data = json.dumps(jsonification, indent=4)
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

        CHATS[int(chat_id)] = deserialized_chat
    
def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)



def main():
    """Start the bot"""
    
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #
    # Database connection (needed for deploying the app on Heroku)
    #
    # heroku pg:psql postgresql-solid-47100 --app fioriktos
    #
    # create table fioriktos (
    #     id serial primary key,
    #     json varchar(65536) not null
    # );
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  #
    connection = psycopg2.connect(DATABASE_URL, sslmode='require')

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM fioriktos ORDER BY id ASC;")
    records = cursor.fetchall()
    
    stored_data = ''.join( [row[1] for row in records] )
    if stored_data != '':
        unjsonify(stored_data)

    cursor.close()
    connection.close()



    # Create the EventHandler and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("fioriktos", fioriktos))
    dp.add_handler(CommandHandler("torrent", torrent, pass_args=True))
    dp.add_handler(CommandHandler("enablelearning", enable_learning))
    dp.add_handler(CommandHandler("disablelearning", disable_learning))
    dp.add_handler(CommandHandler("serialize", serialize))
    dp.add_handler(CommandHandler("debug", debug))

    # on noncommand i.e message
    dp.add_handler(MessageHandler(Filters.text, learn_text_and_reply))
    dp.add_handler(MessageHandler(Filters.sticker, learn_sticker_and_reply))
    dp.add_handler(MessageHandler(Filters.animation, learn_animation_and_reply))
    dp.add_handler(MessageHandler(Filters.document, deserialize))

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
