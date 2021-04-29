from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from os import environ, mkdir
from functools import wraps
from hashlib import md5
import langdetect
import datetime
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
BOT_ID                = int(BOT_TOKEN[:BOT_TOKEN.find(':')])
ADMIN                 = int(environ.get("ADMIN"))
HEROKU_APP_NAME       = environ.get("HEROKU_APP_NAME")
DATABASE_URL          = environ.get("DATABASE_URL")
PORT                  = int(environ.get("PORT", "8443"))
AWS_ACCESS_KEY_ID     = environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
REGION_NAME           = environ.get("REGION_NAME")
S3_BUCKET_NAME        = environ.get("S3_BUCKET_NAME")



""" Constants """
BEGIN                    = ""
END                      = 0
ENDING_PUNCTUATION_MARKS = ".!?\n"
MESSAGE                  = "Message"
STICKER                  = "Sticker"
ANIMATION                = "Animation"
AUDIO                    = "Audio"

PREFIX                   = "chats/"
TO_KEY                   = lambda chat_id: PREFIX + str(chat_id) + ".txt"

LANG_TO_VOICE = {
    'af':    'Ruben',    # redirect Afrikaans to Dutch
    'ar':    'Zeina',
    'bg':    'Maxim',    # redirect Bulgarian to Russian
    'ca':    'Miguel',   # redirect Catalan to Spanish
    'cs':    'Maxim',    # redirect Czech to Russian
    'cy':    'Gwyneth',
    'da':    'Mads',
    'de':    'Hans',
    'en':    'Joey',
    'es':    'Miguel',
    'fa':    'Zeina',    # redirect Farsi to Arabic
    'fr':    'Mathieu',
    'hi':    'Aditi',
    'hr':    'Maxim',    # redirect Croatian to Russian
    'is':    'Karl',
    'it':    'Giorgio',
    'ja':    'Takumi',
    'ko':    'Seoyeon',
    'mk':    'Maxim',    # redirect Macedonian to Russian
    'mr':    'Aditi',    # redirect Marathi to Hindi
    'ne':    'Aditi',    # redirect Nepali to Hindi
    'nl':    'Ruben',
    'no':    'Liv',
    'pl':    'Jacek',
    'pt':    'Ricardo',
    'ro':    'Carmen',
    'ru':    'Maxim',
    'sl':    'Maxim',    # redirect Slovene to Russian
    'sk':    'Maxim',    # redirect Slovak to Russian
    'sv':    'Astrid',
    'tr':    'Filiz',
    'uk':    'Maxim',    # redirect Ukrainian to Russian
    'zh-cn': 'Zhiyu',
    'zh-tw': 'Zhiyu'
}

GDPR = "To work correctly, I need to store these information for each chat:" + \
       "\n- Chat ID" + \
       "\n- Sent words" + \
       "\n- Sent stickers" + \
       "\n- Sent gifs" + \
       "\nI don't store any information about users, such as user ID, username, profile picture..." + \
       "\nData are automatically deleted after 90 days of inactivity." + \
       "\nFurther commands can be used to better control your data:" + \
       "\n- /gdpr download : Retrieve the data for the current chat on a text file." + \
       "\n- /gdpr delete : Remove all data for the current chat. NOTE: this operation is irreversible and you will NOT be asked a confirmation!" + \
       "\n- /gdpr flag : Reply to a sticker or a gif with this command to remove it from my memory. This is useful to prevent me from spamming inappropriate content." + \
       "\n- /gdpr unflag : Allow me to learn a sticker or gif that was previously flagged." + \
       "\nFor more information, visit https://www.github.com/FiorixF1/fioriktos-bot.git or contact my developer @FiorixF1."

WELCOME = "Hi! I am Fioriktos and I can learn how to speak! You can interact with me using the following commands:" + \
          "\n- /fioriktos : Let me generate a message" + \
          "\n- /sticker : Let me send a sticker" + \
          "\n- /gif : Let me send a gif" + \
          "\n- /audio : Let me send an audio" + \
          "\n- /torrent n : Let me reply automatically to messages sent by others. The parameter n sets how much talkative I am and it must be a number between 0 and 10: with /torrent 10 I will answer all messages, while /torrent 0 will mute me." + \
          "\n- You can enable or disable my learning ability with the commands /enablelearning and /disablelearning" + \
          "\n- /thanos : This command will delete half the memory of the chat. Use it wisely!" + \
          "\n- /bof : If I say something funny, you can make a screenshot and send it with this command in the description. Your screenshot could get published on @BestOfFioriktos. In case of an audio message, just reply to it with /bof" + \
          "\n- /gdpr : Here you can have more info about privacy, special commands and visit my source code 💻"



""" Global objects """
MEMORY_MANAGER = None



""" This class handles data storage and synchronization (FullRam edition) """
class MemoryManagerFullRam:
    def __init__(self):
        self.chats = dict()             # key = chat_id --- value = object Chat
        self.last_sync = time.time()    # for automatic serialization on database

    def get_chat_from_id(self, chat_id):
        try:
            chat = self.chats[chat_id]
        except:
            chat = Chat()
            self.chats[chat_id] = chat
        chat.last_update = time.time()
        
        logger.info("RAM: {} - DISK: N/A - NETWORK: N/A".format(len(self.chats)))
        
        return chat

    def synchronize(self):
        now = time.time()
        if now - self.last_sync > 666:  # 37% rule
            self.delete_old_chats()
            self.thanos_big_chats()
            self.store_db()
            self.last_sync = now

    def load_db(self):
        try:
            s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
            dump = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key="dump.txt")
            data = dump['Body'].read()
            self.unjsonify(data)
        except Exception as e:
            # cold start: 'dump.txt' does not exist yet
            logger.error("Exception occurred: {}".format(e))
            data = '{}'
        return data

    def store_db(self):
        data = self.jsonify()
        s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
        s3_client.put_object(Body=data.encode(), Bucket=S3_BUCKET_NAME, Key="dump.txt")
        return data

    def jsonify(self):
        jsonification = dict()
        for chat_id in self.chats:
            jsonification[chat_id] = str(self.chats[chat_id])
        data = json.dumps(jsonification, indent=2)
        return data

    def unjsonify(self, data):
        chats_tmp = json.loads(data)

        for chat_id in chats_tmp:
            jsonized_chat = json.loads(chats_tmp[chat_id])

            deserialized_chat = Chat()
            deserialized_chat.torrent_level = jsonized_chat.get("torrent_level", 5)
            deserialized_chat.is_learning = jsonized_chat.get("is_learning", True)
            deserialized_chat.model = jsonized_chat.get("model", { BEGIN: [END] })
            deserialized_chat.stickers = jsonized_chat.get("stickers", [])
            deserialized_chat.animations = jsonized_chat.get("animations", [])
            deserialized_chat.flagged_media = set(jsonized_chat.get("flagged_media", []))
            deserialized_chat.last_update = jsonized_chat.get("last_update", time.time())

            self.chats[int(chat_id)] = deserialized_chat

    def delete_old_chats(self):
        now = time.time()
        for chat_id in list(self.chats.keys()):
            if now - self.chats[chat_id].last_update > 7776000:
                del self.chats[chat_id]

    def thanos_big_chats(self):
        for chat_id in list(self.chats.keys()):
            if len(self.chats[chat_id].model) > 25000:
                self.chats[chat_id].halve()
                self.chats[chat_id].clean()

    def download_chat(self, chat):
        data = str(chat)
        with open("dump.txt", "w") as dump:
            dump.write(data)
        return "dump.txt"

    def delete_chat(self, chat_id):
        del self.chats[update.message.chat_id]



""" This class handles data storage and synchronization (ThreeLevelCache edition) """
class MemoryManagerThreeLevelCache:
    def __init__(self):
        self.chats         = dict()         # key = chat_id [integer] --- value = Chat [object]
        self.disk_chats    = set()          # chats in local storage: set of chat_key [string]
        self.network_chats = set()          # chats in remote storage: set of chat_key [string]
        self.last_sync     = time.time()    # for automatic serialization on database

    def get_chat_from_id(self, chat_id):
        # implement a three-level cache hierarchy: RAM > local storage > remote storage
        chat_key = TO_KEY(chat_id)
        if chat_id in self.chats:
            chat = self.chats[chat_id]
        elif chat_key in self.disk_chats:
            with open(chat_key, "r") as dump:
                data = dump.read()
            chat = self.unjsonify(data)
            self.chats[chat_id] = chat
        elif chat_key in self.network_chats:
            s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
            dump = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=chat_key)
            data = dump['Body'].read()
            chat = self.unjsonify(data)
            self.chats[chat_id] = chat
        else:
            chat = Chat()
            self.chats[chat_id] = chat 
        chat.last_update = time.time()

        logger.info("RAM: {} - DISK: {} - NETWORK: {}".format(len(self.chats), len(self.disk_chats), len(self.network_chats)))
        
        return chat

    def synchronize(self):
        now = time.time()
        if now - self.last_sync > 666:  # 37% rule
            self.thanos_big_chats()
            self.store_db()
            self.last_sync = now

    def load_db(self):
        try:
            s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
            chats_aws = s3_client.list_objects(Bucket=S3_BUCKET_NAME, Prefix=PREFIX)["Contents"][1:]    
            
            now = time.time()
            for chat_aws in chats_aws:
                if now - chat_aws["LastModified"].timestamp() > 7776000:
                    # no need to remove from local storage: in Heroku it is freed at boot
                    s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=chat_aws["Key"])
                else:
                    self.network_chats.add(chat_aws["Key"])
        except Exception as e:
            # cold start: 'chats/' does not exist yet
            logger.error("Exception occurred: {}".format(e))

        # create directory in local storage or everything will break :)
        try:
            mkdir(PREFIX)
        except:
            pass

    def store_db(self):
        s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)

        remove_from_RAM = []
        for chat_id in self.chats:
            current_chat = self.chats[chat_id]
            chat_key = TO_KEY(chat_id)
            
            if current_chat.dirty_bit:
                data = self.jsonify(current_chat)
                s3_client.put_object(Body=data.encode(), Bucket=S3_BUCKET_NAME, Key=chat_key)
                current_chat.dirty_bit = 0
                self.network_chats.add(chat_key)
            else:
                data = self.jsonify(current_chat)
                with open(chat_key, "w") as dump:
                    dump.write(data)
                self.disk_chats.add(chat_key)
                remove_from_RAM.append(chat_id)

        for chat_id in remove_from_RAM:
            del self.chats[chat_id]

    def jsonify(self, chat):
        serialized_chat = str(chat)
        return serialized_chat

    def unjsonify(self, data):
        jsonized_chat = json.loads(data)

        deserialized_chat = Chat()
        deserialized_chat.torrent_level = jsonized_chat.get("torrent_level", 5)
        deserialized_chat.is_learning = jsonized_chat.get("is_learning", True)
        deserialized_chat.model = jsonized_chat.get("model", { BEGIN: [END] })
        deserialized_chat.stickers = jsonized_chat.get("stickers", [])
        deserialized_chat.animations = jsonized_chat.get("animations", [])
        deserialized_chat.flagged_media = set(jsonized_chat.get("flagged_media", []))
        deserialized_chat.last_update = jsonized_chat.get("last_update", time.time())

        return deserialized_chat

    def thanos_big_chats(self):
        for chat_id in self.chats:
            if len(self.chats[chat_id].model) > 25000:
                self.chats[chat_id].halve()
                self.chats[chat_id].clean()

    def download_chat(self, chat):
        data = self.jsonify(chat)
        with open("dump.txt", "w") as dump:
            dump.write(data)
        return "dump.txt"

    def delete_chat(self, chat_id):
        # no need to remove from local storage: in Heroku it is freed at boot
        chat_key = TO_KEY(chat_id)
        if chat_key in self.network_chats:
            # if the chat has been created recently, it may not be on S3
            s3_client = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=TO_KEY(update.message.chat_id))
            self.network_chats.remove(TO_KEY(chat_id))
        # remove from RAM
        del self.chats[chat_id]



def create_memory_manager(name):
    if name == "FullRam":
        return MemoryManagerFullRam()
    if name == "ThreeLevelCache":
        return MemoryManagerThreeLevelCache()



""" This class handles the data for a single chat, including Fiorix chain generation """
class Chat:
    def __init__(self):
        self.torrent_level = 5
        self.is_learning = True
        self.model = { BEGIN: [END] }
        self.stickers = []
        self.animations = []
        self.flagged_media = set()
        self.last_update = time.time()
        self.dirty_bit = 1

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
        if self.is_learning and sticker not in self.flagged_media:
            if len(self.stickers) < 1024:
                self.stickers.append(sticker)
            else:
                guess = random.randint(0, 1023)
                self.stickers[guess] = sticker

    def learn_animation(self, animation):
        if self.is_learning and animation not in self.flagged_media:
            if len(self.animations) < 1024:
                self.animations.append(animation)
            else:
                guess = random.randint(0, 1023)
                self.animations[guess] = animation

    def reply(self):
        if random.random()*10 < self.torrent_level**2/10:
            if random.random()*10 < 9.0:
                return (MESSAGE, self.talk())
            else:
                type_of_reply = random.choice([STICKER, ANIMATION, AUDIO])
                if type_of_reply == STICKER:
                    return (STICKER, self.choose_sticker())
                elif type_of_reply == ANIMATION:
                    return (ANIMATION, self.choose_animation())
                elif type_of_reply == AUDIO:
                    return (AUDIO, self.choose_audio())
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

    def speech(self):
        text = self.talk()
        
        try:
            candidates = langdetect.detect_langs(text)
            winner = random.choice(candidates).lang
            voice = LANG_TO_VOICE[winner]
        except Exception as e:
            # language detection unsuccessful or unsupported language
            logger.error("Exception occurred: {}".format(e))
            # fallback to Italian
            voice = LANG_TO_VOICE['it']

        polly_client = boto3.client("polly", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=REGION_NAME)
        response = polly_client.synthesize_speech(VoiceId=voice,
                                                  OutputFormat='mp3',
                                                  Text=text)
        with open("audio.mp3", "wb") as audio:
            audio.write(response['AudioStream'].read())
        return "audio.mp3"

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

    def choose_audio(self):
        try:
            return self.speech()
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

    def flag(self, item):
        while item in self.stickers:
            self.stickers.remove(item)
        while item in self.animations:
            self.animations.remove(item)
        self.flagged_media.add(item)

    def unflag(self, item):
        if item in self.flagged_media:
            self.flagged_media.remove(item)

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
                         "flagged_media": list(self.flagged_media),
                         "last_update": self.last_update}
        return json.dumps(jsonification)



""" Decorators """
def restricted(f):
    @wraps(f)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        username = update.effective_user.username
        if user_id != ADMIN:
            logger.warning("Unauthorized access denied for {} ({}).".format(user_id, username))
            return
        f(update, context, *args, **kwargs)
    return wrapped

def chat_finder(f):
    @wraps(f)
    def wrapped(update, context, *args, **kwargs):
        chat_id = update.message.chat_id
        chat = MEMORY_MANAGER.get_chat_from_id(chat_id)
        f(update, context, chat, *args, **kwargs)
    return wrapped

def serializer(f):
    @wraps(f)
    def wrapped(update, context, *args, **kwargs):
        f(update, context, *args, **kwargs)
        MEMORY_MANAGER.synchronize()
    return wrapped



""" Commands """
def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text="SYN")

def help(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text=WELCOME)

@serializer
@chat_finder
def fioriktos(update, context, chat):
    reply = chat.talk()
    if reply != "":
        context.bot.send_message(chat_id=update.message.chat_id, text=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty chain")

@serializer
@chat_finder
def choose_sticker(update, context, chat):
    reply = chat.choose_sticker()
    if reply != "":
        context.bot.send_sticker(chat_id=update.message.chat_id, sticker=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty sticker set")

@serializer
@chat_finder
def choose_animation(update, context, chat):
    reply = chat.choose_animation()
    if reply != "":
        context.bot.send_animation(chat_id=update.message.chat_id, animation=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty gif set")

@serializer
@chat_finder
def choose_audio(update, context, chat):
    reply = chat.choose_audio()
    if reply != "":
        context.bot.send_voice(chat_id=update.message.chat_id, voice=open(reply, 'rb'))
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Empty chain")

@serializer
@chat_finder
def torrent(update, context, chat):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.message.chat_id, text="Torrent level is {}\n\nChange with /torrent followed by a number between 0 and 10.".format(chat.get_torrent()))
    else:
        try:
            quantity = int(context.args[0])
            if quantity < 0 or quantity > 10:
                context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Send /torrent with a number between 0 and 10.")
            else:
                chat.set_torrent(quantity)
                context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
        except:
            context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Send /torrent with a number between 0 and 10.")

@serializer
@chat_finder
def enable_learning(update, context, chat):
    chat.enable_learning()
    context.bot.send_message(chat_id=update.message.chat_id, text="Learning enabled")

@serializer
@chat_finder
def disable_learning(update, context, chat):
    chat.disable_learning()
    context.bot.send_message(chat_id=update.message.chat_id, text="Learning disabled")

@serializer
@chat_finder
def thanos(update, context, chat):
    try:
        expected = md5(str(update.message.chat_id).encode()).hexdigest().upper()
        real = context.args[0]
        if real != expected:
            context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Send this message to delete half the memory of this chat.")
            context.bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="ACK // Currently this chat has {} words, {} stickers and {} gifs for a total size of {} bytes. Let's do some cleaning.".format(len(chat.model),
                                                                                                                                                                                                  len(chat.stickers),
                                                                                                                                                                                                  len(chat.animations),
                                                                                                                                                                                                  len(str(chat).encode())))
            time.sleep(6)
            context.bot.send_animation(chat_id=update.message.chat_id, animation=open('thanos.mp4', 'rb'))            
            
            # destroy half the chat
            chat.halve()
            # delete isolated words
            chat.clean()
            
            time.sleep(6)
            context.bot.send_message(chat_id=update.message.chat_id, text="Now this chat contains {} words, {} stickers and {} gifs for a total size of {} bytes.".format(len(chat.model),
                                                                                                                                                                  len(chat.stickers),
                                                                                                                                                                  len(chat.animations),
                                                                                                                                                                  len(str(chat).encode())))
    except:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Send this message to delete half the memory of this chat.")
        context.bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))

def bof(update, context):
    if update.message.reply_to_message and update.message.reply_to_message.audio:
        context.bot.send_audio(chat_id=ADMIN, audio=update.message.reply_to_message.audio)
        context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
    elif update.message.reply_to_message and update.message.reply_to_message.voice:
        context.bot.send_voice(chat_id=ADMIN, voice=update.message.reply_to_message.voice)
        context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
    elif not update.message.photo:
        context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Reply to an audio message with /bof or send a screenshot with /bof in the description, you could get published on @BestOfFioriktos")
    elif update.message.caption and ("/bof" in update.message.caption or "/bestoffioriktos" in update.message.caption):
        context.bot.send_photo(chat_id=ADMIN, photo=update.message.photo[-1])
        context.bot.send_message(chat_id=update.message.chat_id, text="ACK")

@serializer
@chat_finder
def learn_text_and_reply(update, context, chat):
    chat.learn_text(update.message.text)
    reply(update, context, chat)

@serializer
@chat_finder
def learn_sticker_and_reply(update, context, chat):
    chat.learn_sticker(update.message.sticker.file_id)
    reply(update, context, chat)

@serializer
@chat_finder
def learn_animation_and_reply(update, context, chat):
    chat.learn_animation(update.message.animation.file_id)
    reply(update, context, chat)

@serializer
@chat_finder
def gdpr(update, context, chat):
    # this code is a bit messed up
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.message.chat_id, text=GDPR)
    else:
        command = context.args[0].lower()
        if command == "download":
            filename = MEMORY_MANAGER.download_chat(chat)
            context.bot.send_document(chat_id=update.message.chat_id, document=open(filename, "rb"))
        elif command == "delete":
            MEMORY_MANAGER.delete_chat(update.message.chat_id)
            context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
        elif command == "flag":
            if update.message.reply_to_message:
                # identify item
                if update.message.reply_to_message.sticker:
                    item = update.message.reply_to_message.sticker.file_id
                elif update.message.reply_to_message.animation:
                    item = update.message.reply_to_message.animation.file_id
                else:
                    context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Reply to a sticker or a gif with /gdpr flag")
                    return
                # remove from bot memory
                chat.flag(item)
                # remove from chat history (if admin)
                myself = context.bot.getChatMember(update.message.chat_id, BOT_ID)
                if myself["status"] == "administrator" and myself["can_delete_messages"]:
                    context.bot.delete_message(update.message.chat_id, update.message.reply_to_message.message_id)
                # done
                context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
            else:
                context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Reply to a sticker or a gif with /gdpr flag")
        elif command == "unflag":
            if update.message.reply_to_message:
                # identify item
                if update.message.reply_to_message.sticker:
                    item = update.message.reply_to_message.sticker.file_id
                elif update.message.reply_to_message.animation:
                    item = update.message.reply_to_message.animation.file_id
                else:
                    context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Reply to a sticker or a gif with /gdpr unflag")
                    return
                # update bot memory
                chat.unflag(item)
                # done
                context.bot.send_message(chat_id=update.message.chat_id, text="ACK")
            else:
                context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Reply to a sticker or a gif with /gdpr unflag")
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="NAK // Undefined command after /gdpr")

@serializer
@chat_finder
def welcome(update, context, chat):
    # send welcome message only when added to new chat
    if len(chat.model) == 1:
        for member in update.message.new_chat_members:
            if member.username == 'FioriktosBot':
                context.bot.send_message(chat_id=update.message.chat_id, text=WELCOME)

def reply(update, context, chat):
    response = chat.reply()

    if len(response) == 2:
        type_of_response = response[0]
        content = response[1]

        if content != "":
            if type_of_response == MESSAGE:
                context.bot.send_message(chat_id=update.message.chat_id, text=content)
            elif type_of_response == STICKER:
                context.bot.send_sticker(chat_id=update.message.chat_id, sticker=content)
            elif type_of_response == ANIMATION:
                context.bot.send_animation(chat_id=update.message.chat_id, animation=content)
            elif type_of_response == AUDIO:
                context.bot.send_voice(chat_id=update.message.chat_id, voice=open(content, 'rb'))

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)



def main():
    """Start the bot"""

    # Create memory manager and restore data
    global MEMORY_MANAGER
    MEMORY_MANAGER = create_memory_manager("ThreeLevelCache")   # "FullRam" | "ThreeLevelCache"
    MEMORY_MANAGER.load_db()

    # Create the EventHandler and pass it your bot's token
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("fioriktos", fioriktos))
    dp.add_handler(CommandHandler("sticker", choose_sticker))
    dp.add_handler(CommandHandler("gif", choose_animation))
    dp.add_handler(CommandHandler("audio", choose_audio))
    dp.add_handler(CommandHandler("torrent", torrent))
    dp.add_handler(CommandHandler("enablelearning", enable_learning))
    dp.add_handler(CommandHandler("disablelearning", disable_learning))
    dp.add_handler(CommandHandler("thanos", thanos))
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
                          url_path=BOT_TOKEN,
                          webhook_url="https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, BOT_TOKEN),
                          allowed_updates=["message", "channel_post", "my_chat_member"],
                          drop_pending_updates=True)
    updater.bot.set_webhook(url="https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, BOT_TOKEN),
                            max_connections=100,
                            allowed_updates=["message", "channel_post", "my_chat_member"],
                            drop_pending_updates=True)

if __name__ == '__main__':
    main()
