# fioriktos-bot

This is a Telegram bot which uses Markov chains to learn how to speak given the messages of other users. It can answer with text messages, but also stickers and animations. These are the available commands:
```
    fioriktos - Talk
    sticker - Send a sticker
    gif - Send a gif
    torrent - Automatic replies
    enablelearning - Enable learning
    disablelearning - Disable learning
    bof - Best of Fioriktos
    gdpr - Privacy stuff
```

The extra command ```serialize``` can be issued only by the administrator of the bot. It serializes the bot state into a file sent to the administrator. This makes possible for the administrator to shutdown the bot without loosing the learnt models or to transfer them in other groups without starting from an empty model.

The bot is deployed on Heroku, which erases the local file system every 24 hours. For this reason the code is a bit tricky, it uses a local connection to a Postgres database in order to store the learnt models.
