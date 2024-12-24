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
    restrict - Limit commands to admins
    gdpr - Privacy stuff
```

There are a number of extra commands that can be issued through ```/gdpr```, namely:
* ```/gdpr download``` : Download all the data for the current chat in a text file, so that a user can inspect them.
* ```/gdpr delete``` : Erase the entire content of the current chat in one shot. Be careful when using this function: the deletion of your data will happen without asking confirmation and is not reversible, so do it wisely.
* ```/gdpr flag``` : Remove a specific sticker or gif from Fioriktos' memory. Let's say some troll publishes a porn gif in your group. Instead of deleting it, reply to it with ```/gdpr flag```, this way the gif will be removed from the bot's memory and Fioriktos won't publish it again later. If the bot has administrator rights, it will also care about deleting the message from group history. The operation can be undone with ```/gdpr unflag```.
* ```/gdpr tx``` : If you want to transfer the data stored by Fioriktos from one chat to another, first send this command in the source chat. The bot will answer with a code that must be sent in the target chat to complete the transfer. The code will be available for up to ten minutes (five minutes on average) and it is something like ```/gdpr rx DEADBEEF```.

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

## What is assuring me that you won't read my private messages?

As I said, Fioriktos is not storing the whole messages, but only the words composing them, so it is not technically possible to recover the original messages. Anyway, I would like to remark that, whenever you use a Telegram bot which has access to all messages you send, you are accepting the risk that the bot owner will use your data unfairly. If you use a bot which is closed source and you do not know where it is deployed, how it works, what data it stores and even who are the people managing it, nothing can guarantee that the unknown developers are not storing all your conversations in some hidden server on the Pacific Islands or worse they are collecting your pictures and videos to feed some deepfake algorithm. Every bot which both implements Markov chains and is closed source could potentially do this without our knowledge nor permission (I am thinking about a very famous one). With Fioriktos, you know exactly how it works (see the code ;) ), where it is deployed, what it stores and who is developing it (hello there!). In this scenario, I feel much more secure.

## Can I clone this project and make my custom version of Fioriktos?

Of course you can, and I even encourage people to do so. If you want to create a copy of Fioriktos, one possibility is to replicate its exact working environment. To do this, you need:
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

Another possibility, useful for development and testing, is running the bot locally on your computer. In this case, you don't need an account on AWS or Heroku. Just make sure you have installed Python 3.10.13 and the dependencies listed in ```requirements.txt```, set the ```BOT_TOKEN``` and ```ADMIN``` environment variables, then launch ```python FioriktosBot.py LocalThreeLevelCache``` on terminal and enjoy!

Note that Fioriktos takes a command-line parameter when it is launched, that is the so called "memory manager". It's a class that describes how and where data shall be collected. Currently there are three memory managers implemented:
* *HerokuS3ThreeLevelCache*: this is the manager in use for the official release of Fioriktos. It is based on Heroku as hosting service and S3 for storing data, while active chats are managed through a three level cache strategy (RAM + local disk + remote network) to minimize the usage of RAM. In this manager, each chat has its own text file with data and it is loaded into RAM only when requested.
* *HerokuS3FullRam*: based on Heroku and S3 like the previous manager, but there is no multilevel cache for storing active chats. All existing chats are stored in a single giant file that is loaded into RAM.
* *LocalTwoLevelCache*: it's the manager to be used for deploying locally. It uses the multilevel cache for managing active chats, but does not communicate with AWS and is not integrated in the Heroku platform. It works out of the box on a common PC.

As you can imagine, custom managers for different hosting services or databases can be created by anyone to better fit their needs. You just need to start from the existing ones and reimplement their functions. Then, in ```FioriktosBot.py```, inside function ```register_environment_managers```, add your own custom manager. Consider also that each memory manager and the ```Global.py``` source file also contain a set of constant values (numbers and strings) that can be changed easily for common customization.

At this point, you have created a working copy of Fioriktos. Now you can make all changes you desire to your GitHub fork and deploy those changes to Heroku or anywhere else at any time. Have fun!

## Support the project

The bot unfortunately does not run for free. Amazon S3 must be paid, and since November 2022 Heroku has removed the free plan from their products, hence it must be paid as well. As a result, a simplistic bot created for fun has become too much expensive for me. For this reason, I opened an account on *Buy me a Coffee* so that you can contribute to keep the bot running. The objective is to keep a fund of 15 € per month, which is a lot for a single person, but they become a little quantity if divided among many people. You can contribute through single donations or by subscribing to one of the following tiers:
* Bronze 🥉 level 2€ / month
* Silver 🥈 level 5€ / month
* Gold 🥇 level 8€ / month

<img src="https://www.buymeacoffee.com/assets/img/guidelines/download-assets-sm-1.svg" alt="Buymeacoffee logo" width=100/> - [Buy me a coffee](https://www.buymeacoffee.com/fiorixf2W)

Thanks for your support!
