from telegram.ext import CommandHandler, MessageHandler, Filters
from functools import wraps
from hashlib import md5
import logging
import random
import time
import sys

import Global
import Chat



# Enable log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)



""" Global objects """
ENVIRONMENT_MANAGER = None



def register_environment_managers():
    import HerokuS3FullRam
    import HerokuS3ThreeLevelCache
    import LocalThreeLevelCache
    
    return {
        "HerokuS3FullRam": HerokuS3FullRam.HerokuS3FullRam,
        "HerokuS3ThreeLevelCache": HerokuS3ThreeLevelCache.HerokuS3ThreeLevelCache,
        "LocalThreeLevelCache": LocalThreeLevelCache.LocalThreeLevelCache
    }



""" Decorators """
def chat_finder(f):
    @wraps(f)
    def wrapped(update, context, *args, **kwargs):
        chat_id = update.message.chat_id
        chat = ENVIRONMENT_MANAGER.get_chat_from_id(chat_id)
        f(update, context, chat, *args, **kwargs)
    return wrapped

def serializer(f):
    @wraps(f)
    def wrapped(update, context, *args, **kwargs):
        f(update, context, *args, **kwargs)
        ENVIRONMENT_MANAGER.synchronize()
    return wrapped



""" Commands """
def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text=Global.START)

def help(update, context):
    context.bot.send_message(chat_id=update.message.chat_id, text=Global.WELCOME)

@serializer
@chat_finder
def fioriktos(update, context, chat):
    reply = chat.talk()
    if reply != "":
        context.bot.send_message(chat_id=update.message.chat_id, text=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Empty chain")

@serializer
@chat_finder
def choose_sticker(update, context, chat):
    reply = chat.choose_sticker()
    if reply != "":
        context.bot.send_sticker(chat_id=update.message.chat_id, sticker=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Empty sticker set")

@serializer
@chat_finder
def choose_animation(update, context, chat):
    reply = chat.choose_animation()
    if reply != "":
        context.bot.send_animation(chat_id=update.message.chat_id, animation=reply)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Empty gif set")

@serializer
@chat_finder
def choose_audio(update, context, chat):
    text = None
    if update.message.reply_to_message and update.message.reply_to_message.text:
        text = update.message.reply_to_message.text
    
    reply = chat.choose_audio(text)
    if reply != "":
        context.bot.send_voice(chat_id=update.message.chat_id, voice=open(reply, 'rb'))
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Empty chain")

@serializer
@chat_finder
def torrent(update, context, chat):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.message.chat_id, text="Torrent level is {}\n\nChange with /torrent followed by a number between 0 and 10.".format(chat.get_torrent()))
    else:
        try:
            quantity = int(context.args[0])
            if quantity < 0 or quantity > 10:
                context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Send /torrent with a number between 0 and 10.")
            else:
                chat.set_torrent(quantity)
                context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)
        except:
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Send /torrent with a number between 0 and 10.")

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
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + \
                " // Currently this chat has {} words, {} stickers and {} gifs for a total size of {} bytes. ".format(len(chat.model),
                                                                                                                      len(chat.stickers),
                                                                                                                      len(chat.animations),
                                                                                                                      len(str(chat).encode())) + \
                "Send this message to delete half the memory of this chat.")
            context.bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK + " // Let's do some cleaning!")
            time.sleep(3)
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
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + \
             " // Currently this chat has {} words, {} stickers and {} gifs for a total size of {} bytes. ".format(len(chat.model),
                                                                                                                   len(chat.stickers),
                                                                                                                   len(chat.animations),
                                                                                                                   len(str(chat).encode())) + \
             "Send this message to delete half the memory of this chat.")
        context.bot.send_message(chat_id=update.message.chat_id, text="/thanos {}".format(expected))

def bof(update, context):
    if update.message.reply_to_message and update.message.reply_to_message.audio and update.message.reply_to_message.from_user.id == Global.BOT_ID:
        context.bot.send_audio(chat_id=Global.ADMIN, audio=update.message.reply_to_message.audio)
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)
    elif update.message.reply_to_message and update.message.reply_to_message.voice and update.message.reply_to_message.from_user.id == Global.BOT_ID:
        context.bot.send_voice(chat_id=Global.ADMIN, voice=update.message.reply_to_message.voice)
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)
    elif not update.message.photo:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Reply to an audio message with /bof or send a screenshot with /bof in the description, you could get published on @BestOfFioriktos")
    elif update.message.caption and ("/bof" in update.message.caption or "/bestoffioriktos" in update.message.caption):
        context.bot.send_photo(chat_id=Global.ADMIN, photo=update.message.photo[-1])
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)

@serializer
@chat_finder
def learn_text_and_reply(update, context, chat):
    chat.learn_text(update.message.text)
    reply(update, context, chat)

@serializer
@chat_finder
def learn_sticker_and_reply(update, context, chat):
    chat.learn_sticker(update.message.sticker.file_id, update.message.sticker.file_unique_id)
    reply(update, context, chat)

@serializer
@chat_finder
def learn_animation_and_reply(update, context, chat):
    chat.learn_animation(update.message.animation.file_id, update.message.animation.file_unique_id)
    reply(update, context, chat)

@serializer
@chat_finder
def gdpr(update, context, chat):
    # this code is a bit messed up
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.message.chat_id, text=Global.GDPR)
    else:
        command = context.args[0].lower()
        if command == "download":
            filename = ENVIRONMENT_MANAGER.download_chat(chat, update.message.chat_id)
            context.bot.send_document(chat_id=update.message.chat_id, document=open(filename, "rb"))
        elif command == "delete":
            ENVIRONMENT_MANAGER.delete_chat(update.message.chat_id)
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)
        elif command == "flag":
            chat_id = update.message.chat_id
            user_id = update.message.from_user.id
            if context.bot.getChatMember(chat_id, user_id)["status"] in ["creator", "administrator"]:
                if update.message.reply_to_message:
                    # identify item
                    if update.message.reply_to_message.sticker:
                        item = update.message.reply_to_message.sticker.file_id
                        unique_id = update.message.reply_to_message.sticker.file_unique_id
                    elif update.message.reply_to_message.animation:
                        item = update.message.reply_to_message.animation.file_id
                        unique_id = update.message.reply_to_message.animation.file_unique_id
                    else:
                        context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Reply to a sticker or a gif with /gdpr flag")
                        return
                    # remove from bot memory
                    chat.flag(item, unique_id)
                    # remove from chat history (if admin)
                    myself = context.bot.getChatMember(chat_id, Global.BOT_ID)
                    if myself["status"] == "administrator" and myself["can_delete_messages"]:
                        context.bot.delete_message(chat_id, update.message.reply_to_message.message_id)
                    # done
                    context.bot.send_message(chat_id=chat_id, text=Global.OK)
                else:
                    context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Reply to a sticker or a gif with /gdpr flag")
            else:
                context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Command available only for admins")
        elif command == "unflag":
            chat_id = update.message.chat_id
            user_id = update.message.from_user.id
            if context.bot.getChatMember(chat_id, user_id)["status"] in ["creator", "administrator"]:
                if update.message.reply_to_message:
                    # identify item
                    if update.message.reply_to_message.sticker:
                        unique_id = update.message.reply_to_message.sticker.file_unique_id
                    elif update.message.reply_to_message.animation:
                        unique_id = update.message.reply_to_message.animation.file_unique_id
                    else:
                        context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Reply to a sticker or a gif with /gdpr unflag")
                        return
                    # update bot memory
                    chat.unflag(unique_id)
                    # done
                    context.bot.send_message(chat_id=chat_id, text=Global.OK)
                else:
                    context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Reply to a sticker or a gif with /gdpr unflag")
            else:
                context.bot.send_message(chat_id=chat_id, text=Global.NOK + " // Command available only for admins")
        elif command == "tx":
            OTP = ENVIRONMENT_MANAGER.transmit_chat(update.message.chat_id)
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK + " // Send this command in the target group to copy there the memory of this chat. This code will expire after 5 minutes.")
            context.bot.send_message(chat_id=update.message.chat_id, text="/gdpr rx {}".format(OTP))
        elif command == "rx":
            if len(context.args) < 2:
                context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Missing parameter")
            else:
                OTP = context.args[1]
                if ENVIRONMENT_MANAGER.receive_chat(update.message.chat_id, OTP):
                    context.bot.send_message(chat_id=update.message.chat_id, text=Global.OK)
                else:
                    context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Unknown or expired code")
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text=Global.NOK + " // Unknown command after /gdpr")

@serializer
@chat_finder
def welcome(update, context, chat):
    # send welcome message only when added to new chat
    if chat.is_empty():
        for member in update.message.new_chat_members:
            if member.username == 'FioriktosBot':
                context.bot.send_message(chat_id=update.message.chat_id, text=Global.WELCOME)

def reply(update, context, chat):
    response = chat.reply()

    if len(response) == 2:
        type_of_response = response[0]
        content = response[1]

        if content != "":
            if type_of_response == Chat.MESSAGE:
                context.bot.send_message(chat_id=update.message.chat_id, text=content)
            elif type_of_response == Chat.STICKER:
                context.bot.send_sticker(chat_id=update.message.chat_id, sticker=content)
            elif type_of_response == Chat.ANIMATION:
                context.bot.send_animation(chat_id=update.message.chat_id, animation=content)
            elif type_of_response == Chat.AUDIO:
                context.bot.send_voice(chat_id=update.message.chat_id, voice=open(content, 'rb'))

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if context.error == "Not enough rights to send text messages to the chat":
        bot.leave_chat(update.effective_chat.id)



def main():
    """Start the bot"""

    # Create memory manager and restore data
    ALLOWED_MANAGERS = register_environment_managers()
    if len(sys.argv) < 2 or sys.argv[1] not in ALLOWED_MANAGERS:
        logger.error("Manager must be one of these: {}".format(ALLOWED_MANAGERS.keys()))
        exit()

    global ENVIRONMENT_MANAGER
    ENVIRONMENT_MANAGER = ALLOWED_MANAGERS.get(sys.argv[1])(logger)
    ENVIRONMENT_MANAGER.load_db()

    # Create the EventHandler and pass it your bot's token
    updater = ENVIRONMENT_MANAGER.get_updater()

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
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), learn_text_and_reply))
    dp.add_handler(MessageHandler(Filters.sticker, learn_sticker_and_reply))
    dp.add_handler(MessageHandler(Filters.animation, learn_animation_and_reply))
    dp.add_handler(MessageHandler(Filters.photo, bof))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    
    # log all errors
    dp.add_error_handler(error)

    # start the bot
    ENVIRONMENT_MANAGER.start(updater)
    
if __name__ == '__main__':
    main()
