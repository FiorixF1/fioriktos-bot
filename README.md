# Fioriktos

This is a Telegram bot which uses Markov chains to learn how to speak from the messages of other users. It can answer with text messages, but also stickers, animations and audio messages. These are the available commands:
```
    fioriktos - Talk
    sticker - Send a sticker
    gif - Send a gif
    audio - Send an audio
    torrent - Automatic replies
    enablelearning - Enable learning
    disablelearning - Disable learning
    thanos - Halve the memory of this chat
    bof - Best of Fioriktos
    gdpr - Privacy stuff
```

Since this bot has access to private messages of Telegram group users, it has been designed with a high focus on openness and transparency to guarantee that private data are not used in an improper way. The simple act of making the source code public is already a great step towards this goal, a step which has not been made by other bots similar to Fioriktos.

# FAQ

## Which personal data does Fioriktos store?

Fioriktos is storing a set of data for each chat it is added in. These data consist of:
* Chat ID
* Sent words
* Sent stickers
* Sent gifs

It does not store any information about users, such as user ID, username, profile picture et cetera. Keep in mind that Fioriktos is **not** storing the whole messages sent by users (that would be extremely unpleasant), but only the single words composing them. This is obviously needed to implement Markov chains and generate new messages.

## Where is Fioriktos deployed?

The bot is deployed on Heroku and the learnt models are stored on an Amazon S3 bucket.

## Are my personal data permanently stored?

No. When Fioriktos is removed from a group, the relative data will be automatically deleted after 90 days of inactivity, unless the bot is added to the group again.

Recently we added the possibility for the users to inspect their data and remove them completely in one shot. This is done respectively by the special commands ```/gdpr download``` and ```/gdpr delete```. Be careful when using this function: the deletion of your data will happen without asking confirmation and is not reversible, so do it wisely ;)

## What is assuring me that you won't read my private messages?

As I said, Fioriktos is not storing the whole messages, but only the words composing them, so it is not technically possible to recover the original messages. Anyway, I would like to remark that, whenever you use a Telegram bot which has access to all messages you send, you are accepting the risk that the bot owner will use your data unfairly. If you use a bot which is closed source and you do not know where it is deployed, how it works, what data it stores and even who are the people managing it, nothing can guarantee that the unknown developers are not storing all your conversations in some hidden server on the Pacific Islands or worse they are collecting your pictures and videos to feed some deepfake algorithm. Every bot which both implements Markov chains and is closed source could potentially do this without our knowledge nor permission (I am thinking about a very famous one). With Fioriktos, you know exactly how it works (see the code ;) ), where it is deployed, what it stores and who is developing it (hello there!). In this scenario, I feel much more secure.

## Can I clone this project and make my custom version of Fioriktos?

Of course you can, and I even encourage people to do so. If you want to create a copy of Fioriktos, the easiest way is to replicate its exact working environment. To do this, you need:
* A Telegram account
* A GitHub account
* A Heroku account
* An Amazon Web Services account

Then you have to follow these steps:
1. In **Telegram**, create your new bot through [@BotFather](https://t.me/botfather). You can freely choose its name and profile picture, while as a list of commands, copy-paste the one at the top of this page.
2. In **GitHub**, create a new repository by forking this project.
3. In **Amazon Web Services**, go to *Simple Storage Service* (S3) and create a new bucket. NOTE: this is easier said than done. Creating and configuring an account on AWS is not straightforward. If you need more details on how to do it, look for a video tutorial on YouTube by some smart Indian guy. They are better than official documentation. At the end of this process, you will have many pieces of information: the *AWS Access Key*, the *AWS Secret Access Key*, the region where you created the bucket and the bucket name. You need all these data in the next step.
4. In **Heroku**, create a new project and go to the *Settings* tab. Here you can manage *Config Vars*, which are nothing else than a list of key-value pairs. For the correct working of your bot, you need to set these config vars:
   ```BOT_TOKEN``` = the token of your Telegram bot (you can get it from [@BotFather](https://t.me/botfather))  
   ```ADMIN``` = your Telegram user ID (you can get it from [@userinfobot](https://t.me/userinfobot))  
   ```HEROKU_APP_NAME``` = the name of your Heroku project  
   ```AWS_ACCESS_KEY_ID``` = your AWS Access Key  
   ```AWS_SECRET_ACCESS_KEY``` = your AWS Secret Key  
   ```REGION_NAME``` = the AWS region where you created your bucket  
   ```S3_BUCKET_NAME``` = the name of the bucket

Then, under the *Deploy* tab, you can connect the GitHub repository of your bot to Heroku and deploy it, making it effectively operational on the web. By clicking on *More* > *View logs*, you can watch the logs generated by your application and check if everything is alright or if there are some errors.

At this point, you have created a working copy of Fioriktos. Now you can make all changes you desire to your GitHub fork and deploy those changes to Heroku at any time. Have fun!

