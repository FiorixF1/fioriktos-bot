from telegram.ext import Updater
from os import environ, mkdir, path, remove
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

""" This class handles data storage and synchronization (ThreeLevelCache edition) """
class HerokuS3ThreeLevelCache:
    def __init__(self, logger):
        self.chats         = dict()         # key = chat_id [integer] --- value = Chat [object]
        self.disk_chats    = set()          # chats in local storage: set of chat_key [string]
        self.network_chats = set()          # chats in remote storage: set of chat_key [string]
        self.OTPs          = dict()         # chats ready to be transfered: key = OTP [string] --- value = chat_id [integer]
        self.last_sync     = time.time()    # for automatic serialization on database

        self.HEROKU_APP_NAME       = environ.get("HEROKU_APP_NAME")
        self.PORT                  = int(environ.get("PORT", "8443"))
        self.AWS_ACCESS_KEY_ID     = environ.get("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY = environ.get("AWS_SECRET_ACCESS_KEY")
        self.REGION_NAME           = environ.get("REGION_NAME")
        self.S3_BUCKET_NAME        = environ.get("S3_BUCKET_NAME")
        
        self.PREFIX                = "chats/"
        self.TO_KEY                = lambda chat_id: self.PREFIX + str(chat_id) + ".txt"

        self.CHAT_MAX_DURATION     = 7776000   # seconds in three months
        self.CHAT_UPDATE_TIMEOUT   = 666       # 37 % of 30 minutes
        self.WORD_LIST_MAX_LENGTH  = 16384
        
        self.logger = logger

    def get_chat_from_id(self, chat_id):
        # implement a three-level cache hierarchy: RAM > local storage > remote storage
        chat_key = self.TO_KEY(chat_id)
        if chat_id in self.chats:
            chat = self.chats[chat_id]
        elif chat_key in self.disk_chats:
            with open(chat_key, "r") as dump:
                data = dump.read()
            chat = self.unjsonify(data)
            self.chats[chat_id] = chat
        elif chat_key in self.network_chats:
            s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)
            dump = s3_client.get_object(Bucket=self.S3_BUCKET_NAME, Key=chat_key)
            data = dump['Body'].read()
            chat = self.unjsonify(data)
            self.chats[chat_id] = chat
        else:
            chat = Chat(self)
            self.chats[chat_id] = chat 
        chat.last_update = time.time()

        self.logger.info("RAM: {} - DISK: {} - NETWORK: {}".format(len(self.chats), len(self.disk_chats), len(self.network_chats)))
        
        return chat

    def synchronize(self):
        now = time.time()
        if now - self.last_sync > self.CHAT_UPDATE_TIMEOUT:  # 37% rule
            self.thanos_big_chats()
            self.store_db()
            self.OTPs.clear()
            self.last_sync = now

    def load_db(self):
        try:
            s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)

            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.S3_BUCKET_NAME, Prefix=self.PREFIX)
            
            now = time.time()
            for page in pages:
                for chat_aws in page["Contents"]:
                    if now - chat_aws["LastModified"].timestamp() > self.CHAT_MAX_DURATION and chat_aws["Key"] != self.PREFIX:
                        # no need to remove from local storage: in Heroku it is freed at boot
                        s3_client.delete_object(Bucket=self.S3_BUCKET_NAME, Key=chat_aws["Key"])
                    else:
                        self.network_chats.add(chat_aws["Key"])
            
        except Exception as e:
            # cold start: 'chats/' does not exist yet
            self.logger.warning("Database not found: executing cold start")

        # create directory in local storage or everything will break :)
        try:
            mkdir(self.PREFIX)
        except:
            pass

    def store_db(self):
        s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)

        remove_from_RAM = []
        for chat_id in self.chats:
            current_chat = self.chats[chat_id]
            chat_key = self.TO_KEY(chat_id)
            
            if current_chat.dirty_bit:
                data = self.jsonify(current_chat)
                s3_client.put_object(Body=data.encode(), Bucket=self.S3_BUCKET_NAME, Key=chat_key)
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

        deserialized_chat = Chat(self)
        deserialized_chat.torrent_level = jsonized_chat.get("torrent_level", DEFAULT_TORRENT_LEVEL())
        deserialized_chat.is_learning = jsonized_chat.get("is_learning", DEFAULT_IS_LEARNING())
        deserialized_chat.model = jsonized_chat.get("model", DEFAULT_MODEL())
        deserialized_chat.stickers = jsonized_chat.get("stickers", DEFAULT_STICKERS())
        deserialized_chat.animations = jsonized_chat.get("animations", DEFAULT_ANIMATIONS())
        deserialized_chat.flagged_media = set(jsonized_chat.get("flagged_media", DEFAULT_FLAGGED_MEDIA()))
        deserialized_chat.last_update = jsonized_chat.get("last_update", DEFAULT_LAST_UPDATE())
        deserialized_chat.restricted_mode = jsonized_chat.get("restricted_mode", DEFAULT_RESTRICTED_MODE())

        return deserialized_chat

    def thanos_big_chats(self):
        for chat_id in self.chats:
            if len(self.chats[chat_id].model) > self.WORD_LIST_MAX_LENGTH:
                self.chats[chat_id].halve()
                self.chats[chat_id].clean()

    def download_chat(self, chat, chat_id):
        data = self.jsonify(chat)
        filename = str(chat_id) + ".txt"
        with open(filename, "w") as dump:
            dump.write(data)
        return filename

    def delete_chat(self, chat_id):
        chat_key = self.TO_KEY(chat_id)
        # remove from S3
        if chat_key in self.network_chats:
            # if the chat has been created recently, it may not be on S3
            s3_client = boto3.client("s3", aws_access_key_id=self.AWS_ACCESS_KEY_ID, aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY, region_name=self.REGION_NAME)
            s3_client.delete_object(Bucket=self.S3_BUCKET_NAME, Key=chat_key)
            self.network_chats.remove(chat_key)
        # remove from local storage
        if chat_key in self.disk_chats:
            remove(chat_key)
            self.disk_chats.remove(chat_key)
        # remove from RAM
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
