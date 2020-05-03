# fioriktos-bot

This is a Telegram bot which uses Markov chains to learn how to speak from the messages of other users. It can answer with text messages, but also stickers and animations. These are the available commands:
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

The extra commands ```serialize``` and ```deserialize``` can be issued only by the administrator of the bot. They serialize the bot state into a file sent to the administrator and vice versa. This makes possible for the administrator to shutdown the bot without loosing the learnt models or to transfer them in other groups without starting from an empty model.

The bot is deployed on Heroku and the learnt models are stored on an Amazon S3 bucket.
