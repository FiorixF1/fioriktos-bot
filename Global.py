from os import environ

SUPPORT_ME = "If you like my work, please make a donation on https://www.buymeacoffee.com/fiorixf2W - this is needed to keep me running!" + \
             "\nYou can contribute through single donations or by subscribing to one of the following tiers:" + \
             "\n- Bronze 🥉 level 2€ / month" + \
             "\n- Silver 🥈 level 5€ / month" + \
             "\n- Gold 🥇 level 8€ / month" + \
             "\n" + \
             "\nThank you!"

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
       "\n- /gdpr tx : If you want to copy the memory of chat A into chat B, issue this command in chat A. You will receive a code to send inside chat B to complete the transfer." + \
       "\nFor more information, visit https://www.github.com/FiorixF1/fioriktos-bot.git or contact my developer @FiorixF1.\n\n" + \
       SUPPORT_ME

WELCOME = "Hi! I am Fioriktos and I can learn how to speak! You can interact with me using the following commands:" + \
          "\n- /fioriktos : Let me generate a message" + \
          "\n- /sticker : Let me send a sticker" + \
          "\n- /gif : Let me send a gif" + \
          "\n- /audio : Let me send an audio" + \
          "\n- /torrent n : Let me reply automatically to messages sent by others. The parameter n sets how much talkative I am and it must be a number between 0 and 10: with /torrent 10 I will answer all messages, while /torrent 0 will mute me." + \
          "\n- You can enable or disable my learning ability with the commands /enablelearning and /disablelearning" + \
          "\n- /thanos : This command will delete half the memory of the chat. Use it wisely!" + \
          "\n- /bof : If I say something funny, you can make a screenshot and send it with this command in the description. Your screenshot could get published on @BestOfFioriktos. In case of an audio message, just reply to it with /bof" + \
          "\n- /gdpr : Here you can have more info about privacy, special commands and visit my source code 💻\n\n" + \
          SUPPORT_ME

START = "SYN"
OK    = "ACK"
NOK   = "NAK"

BOT_TOKEN = environ.get("BOT_TOKEN")
BOT_ID    = int(BOT_TOKEN[:BOT_TOKEN.find(':')])
ADMIN     = int(environ.get("ADMIN"))
