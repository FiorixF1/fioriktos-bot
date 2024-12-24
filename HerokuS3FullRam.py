from os import environ, mkdir, path, remove
from telegram.ext import Updater
import langdetect
import random
import boto3
import json
import time

from Chat import *

LANG_TO_VOICE = {
    'af':    'Ruben',    # redirect Afrikaans to Dutch
    'ar':    'Zeina',
    'bg':    'Maxim',    # redirect Bulgarian to Russian
    'ca':    'Arlet',
    'cs':    'Jacek',    # redirect Czech to Polish
    'cy':    'Gwyneth',
    'da':    'Mads',
    'de':    'Hans',
    'en':    'Joey',
    'es':    'Miguel',
    'et':    'Suvi',     # redirect Estonian to Finnish
    'fa':    'Zeina',    # redirect Farsi to Arabic
    'fi':    'Suvi',
    'fr':    'Mathieu',
    'hi':    'Aditi',
    'hr':    'Jacek',    # redirect Croatian to Polish
    'is':    'Karl',
    'it':    'Giorgio',
    'ja':    'Takumi',
    'ko':    'Seoyeon',
    'mk':    'Maxim',    # redirect Macedonian to Russian
    'mr':    'Aditi',    # redirect Marathi to Hindi
    'nb':    'Liv',
    'ne':    'Aditi',    # redirect Nepali to Hindi
    'nl':    'Ruben',
    'no':    'Liv',
    'pl':    'Jacek',
    'pt':    'Ricardo',
    'ro':    'Carmen',
    'ru':    'Maxim',
    'sl':    'Jacek',    # redirect Slovene to Polish
    'sk':    'Jacek',    # redirect Slovak to Polish
    'sv':    'Astrid',
    'tr':    'Filiz',
    'uk':    'Maxim',    # redirect Ukrainian to Russian
    'zh-cn': 'Zhiyu',
    'zh-tw': 'Zhiyu'
}

""" This class handles data storage and synchronization (FullRam edition) """
class HerokuS3FullRam:
    def __init__(self, logger):
        self.chats     = dict()         # key = chat_id --- value = object Chat
        self.OTPs      = dict()         # chats ready to be transfered: key = OTP [string] --- value = chat_id [integer]
        self.last_sync = time.time()    # for automatic serialization on database

        self.HEROKU_APP_NAME       = environ.get("HEROKU_APP_NAME")
        self.PORT                  = int(environ.get("PORT", "8443"))
        self.AWS_ACCESS_KEY_ID     = environ.get("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
        self.REGION_NAME           = environ.get("REGION_NAME")
        self.S3_BUCKET_NAME        = environ.get("S3_BUCKET_NAME")

        self.CHAT_MAX_DURATION     = 7776000   # seconds in three months
        self.CHAT_UPDATE_TIMEOUT   = 666       # 37 % of 30 minutes
        self.WORD_LIST_MAX_LENGTH  = 16384
        
        self.logger = logger

    def get_chat_from_id(self, chat_id):
        try:
            chat = self.chats[chat_id]
        except:
            chat = Chat(self)
            self.chats[chat_id] = chat
        chat.last_update = time.time()
        
        self.logger.info("RAM: {} - DISK: N/A - NETWORK: N/A".format(len(self.chats)))
        
        return chat

    def synchronize(self):
        now = time.time()
        if now - self.last_sync > self.CHAT_UPDATE_TIMEOUT:  # 37% rule
            self.delete_old_chats()
            self.thanos_big_chats()
            self.store_db()
            self.OTPs.clear()
            self.last_sync = now

    def load_db(self):
        try:
            s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)
            dump = s3_client.get_object(Bucket=self.S3_BUCKET_NAME, Key="dump.txt")
            data = dump['Body'].read()
            self.unjsonify(data)
        except Exception as e:
            # cold start: 'dump.txt' does not exist yet
            self.logger.warning("Database not found: executing cold start")
            data = '{}'
        return data

    def store_db(self):
        data = self.jsonify()
        s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)
        s3_client.put_object(Body=data.encode(), Bucket=self.S3_BUCKET_NAME, Key="dump.txt")
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

            deserialized_chat = Chat(self)
            deserialized_chat.torrent_level = jsonized_chat.get("torrent_level", DEFAULT_TORRENT_LEVEL())
            deserialized_chat.is_learning = jsonized_chat.get("is_learning", DEFAULT_IS_LEARNING())
            deserialized_chat.model = jsonized_chat.get("model", DEFAULT_MODEL())
            deserialized_chat.stickers = jsonized_chat.get("stickers", DEFAULT_STICKERS())
            deserialized_chat.animations = jsonized_chat.get("animations", DEFAULT_ANIMATIONS())
            deserialized_chat.flagged_media = set(jsonized_chat.get("flagged_media", DEFAULT_FLAGGED_MEDIA()))
            deserialized_chat.last_update = jsonized_chat.get("last_update", DEFAULT_LAST_UPDATE())
            deserialized_chat.restricted_mode = jsonized_chat.get("restricted_mode", DEFAULT_RESTRICTED_MODE())

            self.chats[int(chat_id)] = deserialized_chat

    def delete_old_chats(self):
        now = time.time()
        for chat_id in list(self.chats.keys()):
            if now - self.chats[chat_id].last_update > self.CHAT_MAX_DURATION:
                del self.chats[chat_id]

    def thanos_big_chats(self):
        for chat_id in list(self.chats.keys()):
            if len(self.chats[chat_id].model) > self.WORD_LIST_MAX_LENGTH:
                self.chats[chat_id].halve()
                self.chats[chat_id].clean()

    def download_chat(self, chat, chat_id):
        data = str(chat)
        filename = str(chat_id) + ".txt"
        with open(filename, "w") as dump:
            dump.write(data)
        return filename

    def delete_chat(self, chat_id):
        del self.chats[chat_id]

    def transmit_chat(self, tx_chat_id):
        OTP = ''.join([random.choice("0123456789ABCDEF") for i in range(8)])
        self.OTPs[OTP] = tx_chat_id
        return OTP

    def receive_chat(self, rx_chat_id, OTP):
        tx_chat_id = self.OTPs.get(OTP, 0)
        if tx_chat_id == 0:
            return False

        tx = self.chats[tx_chat_id]
        rx = Chat(self)
        rx.torrent_level   = tx.torrent_level
        rx.is_learning     = tx.is_learning
        rx.model           = {key: value[:] for key, value in tx.model.items()}
        rx.stickers        = tx.stickers[:]
        rx.animations      = tx.animations[:]
        rx.flagged_media   = tx.flagged_media.copy()
        rx.last_update     = tx.last_update
        rx.restricted_mode = tx.restricted_mode
        
        self.chats[rx_chat_id] = rx
        del self.OTPs[OTP]
        return True

    def text_to_speech(self, text):
        try:
            candidates = langdetect.detect_langs(text)
            winner = random.choice(candidates).lang
            voice = LANG_TO_VOICE[winner]
        except Exception as e:
            # language detection unsuccessful or unsupported language
            self.logger.error("Exception occurred: {}".format(e))
            # fallback to Italian
            voice = LANG_TO_VOICE['it']

        try:
            polly_client = boto3.client("polly", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)
            response = polly_client.synthesize_speech(VoiceId=voice,
                                                      OutputFormat='mp3',
                                                      Text=text)
        except Exception as e:
            # log some kind of error from AWS
            self.logger.error("Exception occurred: {}".format(e))
            return ""

        with open("audio.mp3", "wb") as audio:
            audio.write(response['AudioStream'].read())
        return "audio.mp3"

    def start(self, updater):
        #updater.start_polling()
        
        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        #updater.idle()

        updater.start_webhook(listen="0.0.0.0",
                              port=self.PORT,
                              url_path=Global.BOT_TOKEN,
                              webhook_url="https://{}.herokuapp.com/{}".format(self.HEROKU_APP_NAME, Global.BOT_TOKEN),
                              allowed_updates=["message", "channel_post", "my_chat_member"],
                              drop_pending_updates=True)
        time.sleep(0.1)
        updater.bot.set_webhook(url="https://{}.herokuapp.com/{}".format(self.HEROKU_APP_NAME, Global.BOT_TOKEN),
                                max_connections=100,
                                allowed_updates=["message", "channel_post", "my_chat_member"],
                                drop_pending_updates=True)

    def get_updater(self):
        return Updater(Global.BOT_TOKEN)
