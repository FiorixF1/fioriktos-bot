# fioriktos-bot

This is a Telegram bot which uses Markov chains to learn how to speak given the messages of other users. It can answer with text messages, but also stickers and animations. These are the available commands:
```
    fioriktos - Talk
    torrent - Automatic replies
    enablelearning - Enable learning
    disablelearning - Disable learning
```

There are two more commands that can be issued only by the administrator of the bot, which are ```debug``` and ```serialize```. The first one prints the internal state of the bot on the terminal of the machine running the bot, it is clearly used for debugging purposes. The second one serializes the bot state into a file sent to the administrator. This makes possible for the administrator to shutdown the bot without loosing the learnt models or to transfer them in other groups without starting from an empty model.