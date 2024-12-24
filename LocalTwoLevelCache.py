from telegram.ext import Updater
from os import environ, fsdecode, listdir, mkdir, path, remove
import langdetect
import random
import json
import time

from Chat import *

""" This class handles data storage and synchronization (Local TwoLevelCache edition) """
class LocalTwoLevelCache:
    def __init__(self, logger):
        self.chats         = dict()         # key = chat_id [integer] --- value = Chat [object]
        self.disk_chats    = set()          # chats in local storage: set of chat_key [string]
        self.OTPs          = dict()         # chats ready to be transfered: key = OTP [string] --- value = chat_id [integer]
        self.last_sync     = time.time()    # for automatic serialization on database

        self.PREFIX                = "chats/"
        self.TO_KEY                = lambda chat_id: self.PREFIX + str(chat_id) + ".txt"

        self.CHAT_MAX_DURATION     = 7776000   # seconds in three months
        self.CHAT_UPDATE_TIMEOUT   = 360       # 6 minutes
        self.WORD_LIST_MAX_LENGTH  = 16384
        
        self.logger = logger

    def get_chat_from_id(self, chat_id):
        # implement a two-level cache hierarchy: RAM > local storage
        chat_key = self.TO_KEY(chat_id)
        if chat_id in self.chats:
            chat = self.chats[chat_id]
        elif chat_key in self.disk_chats:
            with open(chat_key, "r") as dump:
                data = dump.read()
            chat = self.unjsonify(data)
            self.chats[chat_id] = chat
        else:
            chat = Chat(self)
            self.chats[chat_id] = chat 
        chat.last_update = time.time()

        self.logger.info("RAM: {} - DISK: {}".format(len(self.chats), len(self.disk_chats)))
        
        return chat

    def synchronize(self):
        now = time.time()
        if now - self.last_sync > self.CHAT_UPDATE_TIMEOUT:
            self.thanos_big_chats()
            self.store_db()
            self.OTPs.clear()
            self.last_sync = now

    def load_db(self):
        try:
            to_be_deleted = []
            now = time.time()
            for file in listdir(self.PREFIX):
                filename = fsdecode(file)
                this_path = path.join(self.PREFIX, filename)
                if filename.endswith(".txt"):
                    if now - path.getmtime(this_path) > self.CHAT_MAX_DURATION:
                        to_be_deleted.append(this_path)
                    else:
                        self.disk_chats.add(this_path)
            for this_path in to_be_deleted:
                remove(this_path)
        except Exception as e:
            # cold start: 'chats/' does not exist yet
            self.logger.warning("Database not found: executing cold start")

        # create directory in local storage or everything will break :)
        try:
            mkdir(self.PREFIX)
        except:
            pass

    def store_db(self):
        remove_from_RAM = []
        for chat_id in self.chats:
            current_chat = self.chats[chat_id]
            chat_key = self.TO_KEY(chat_id)
            
            if current_chat.dirty_bit:
                data = self.jsonify(current_chat)
                with open(chat_key, "w") as dump:
                    dump.write(data)
                current_chat.dirty_bit = 0
                self.disk_chats.add(chat_key)
            else:
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
        # not supported locally
        return ""

    def start(self, updater):
        updater.start_polling()
            
        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        updater.idle()

    def get_updater(self):
        return Updater(Global.BOT_TOKEN)
