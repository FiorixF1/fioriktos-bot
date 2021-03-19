# Fioriktos

This is a Telegram bot which uses Markov chains to learn how to speak from the messages of other users. It can answer with text messages, but also stickers and animations. These are the available commands:
```
    fioriktos - Talk
    sticker - Send a sticker
    gif - Send a gif
    torrent - Automatic replies
    enablelearning - Enable learning
    disablelearning - Disable learning
    thanos - Halve the memory of this chat
    bof - Best of Fioriktos
    gdpr - Privacy stuff
```

The extra commands ```serialize``` and ```deserialize``` can be issued only by the administrator of the bot: they serialize the bot state into a file or set the bot state from a given file. This makes possible for the administrator to shutdown the bot for maintenance without losing the learnt models or to transfer a model from a group to another one without losing it.

Since this bot has access to private messages of Telegram group users, it has been designed with a high focus on openness and transparency to guarantee that private data are not used in an improper way. The simple act of making the source code public is already a great step towards this goal, a step which has not been made by other bots similar to Fioriktos.

# FAQ

## Which personal data does Fioriktos store?

Fioriktos is storing a set of data for each chat it is added in. These data consist of:
* Chat ID
* Sent words
* Sent stickers
* Sent gifs

It does not store any information about users, such as user ID, username, profile picture et cetera. Keep in mind that Fioriktos is *not* storing the whole messages sent by users (that would be extremely unpleasant), but only the single words composing them. This is obviously needed to implement Markov chains and generate new messages.

## Where is Fioriktos deployed?

The bot is deployed on Heroku and the learnt models are stored on an Amazon S3 bucket.

## Are my personal data permanently stored?

No. When Fioriktos is removed from a group, the relative data will be automatically deleted after 90 days of inactivity, unless the bot is added to the group again.

In an active chat, you can always delete half the memory of it by using the command ```thanos```.

Currently there is no direct way to delete the whole data of a chat in one shot, however you can achieve the same result by issuing ```thanos``` multiple times or you can ask me directly to remove the data of a chat (check @FiorixF1 on Telegram).

## What is assuring me that you won't read my private messages?

As I said, Fioriktos is not storing the whole messages, but only the words composing them, so it is not technically possible to recover the original messages. Anyway, I would like to remark that, whenever you use a Telegram bot which has access to all messages you send, you are accepting the risk that the bot owner will use your data unfairly. If you use a bot which is closed source and you do not know where it is deployed, how it works, what data it stores and even who are the people managing it, nothing can guarantee that the unknown developers are not storing all your conversations in some hidden server on the Pacific Islands or worse they are collecting your pictures and videos to feed some deepfake algorithm. Every bot which both implements Markov chains and is closed source could potentially do this without our knowledge nor permission (I am thinking about a very famous one). With Fioriktos, you know exactly how it works (see the code ;) ), where it is deployed, what it stores and who is developing it (hello there!). In this scenario, I feel much more secure.
