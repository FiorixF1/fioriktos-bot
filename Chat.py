import random
import json
import time

import Global

BEGIN                     = ""
END                       = 0
ENDING_PUNCTUATION_MARKS  = ".!?\n"
MESSAGE                   = "Message"
STICKER                   = "Sticker"
ANIMATION                 = "Animation"
AUDIO                     = "Audio"

DEFAULT_TORRENT_LEVEL     = lambda: 5
DEFAULT_IS_LEARNING       = lambda: True
DEFAULT_MODEL             = lambda: { BEGIN: [END] }
DEFAULT_STICKERS          = lambda: []
DEFAULT_ANIMATIONS        = lambda: []
DEFAULT_FLAGGED_MEDIA     = lambda: set()
DEFAULT_LAST_UPDATE       = lambda: time.time()
DEFAULT_RESTRICTED_MODE   = lambda: False

SUCCESSOR_LIST_MAX_LENGTH = 256
MEDIA_LIST_MAX_LENGTH     = 1024

class Chat:
    def __init__(self, manager):
        self.torrent_level = DEFAULT_TORRENT_LEVEL()
        self.is_learning = DEFAULT_IS_LEARNING()
        self.model = DEFAULT_MODEL()
        self.stickers = DEFAULT_STICKERS()
        self.animations = DEFAULT_ANIMATIONS()
        self.flagged_media = DEFAULT_FLAGGED_MEDIA()
        self.last_update = DEFAULT_LAST_UPDATE()
        self.restricted_mode = DEFAULT_RESTRICTED_MODE()
        self.dirty_bit = 1
        self.manager = manager

    def learn_text(self, text):
        if self.is_learning:
            for sentence in text.split('\n'):
                # pre-processing and filtering
                tokens = sentence.split()
                tokens = [BEGIN] + list(filter(lambda x: "http" not in x, tokens)) + [END]

                # actual learning
                for i in range(len(tokens)-1):
                    token = tokens[i]
                    successor = tokens[i+1]

                    # use the token without special characters
                    filtered_token = self.filter(token)
                    if filtered_token != token:
                        self.model[token] = list()
                        token = filtered_token

                    if token not in self.model:
                        self.model[token] = list()

                    if len(self.model[token]) < SUCCESSOR_LIST_MAX_LENGTH:
                        self.model[token].append(successor)
                    else:
                        guess = random.randint(0, SUCCESSOR_LIST_MAX_LENGTH-1)
                        self.model[token][guess] = successor

    def learn_sticker(self, sticker, unique_id):
        if self.is_learning and unique_id not in self.flagged_media:
            if len(self.stickers) < MEDIA_LIST_MAX_LENGTH:
                self.stickers.append(sticker)
            else:
                guess = random.randint(0, MEDIA_LIST_MAX_LENGTH-1)
                self.stickers[guess] = sticker

    def learn_animation(self, animation, unique_id):
        if self.is_learning and unique_id not in self.flagged_media:
            if len(self.animations) < MEDIA_LIST_MAX_LENGTH:
                self.animations.append(animation)
            else:
                guess = random.randint(0, MEDIA_LIST_MAX_LENGTH-1)
                self.animations[guess] = animation

    def reply(self):
        if random.random()*10 < self.torrent_level**2/10:
            dice = random.random()*10
            if dice < 0.01:
                return (MESSAGE, Global.SUPPORT_ME)
            elif dice < 9.0:
                return (MESSAGE, self.talk())
            else:
                type_of_reply = random.choice([STICKER, ANIMATION, AUDIO])
                if type_of_reply == STICKER:
                    return (STICKER, self.choose_sticker())
                elif type_of_reply == ANIMATION:
                    return (ANIMATION, self.choose_animation())
                elif type_of_reply == AUDIO:
                    return (AUDIO, self.choose_audio())
        return ""

    def talk(self):
        walker = BEGIN if random.random() < 0.5 else random.choice(list(self.model.keys()))
        answer = [walker]
        while True:
            filtered_walker = self.filter(walker)
            if filtered_walker != walker:
                walker = filtered_walker
            new_token = random.choice(self.model[walker])
            # avoid empty messages with non empty model
            if new_token == END and len(answer) == 1 and len(set(self.model[BEGIN])) > 1:
                while new_token == END:
                    new_token = random.choice(self.model[BEGIN])
            if new_token == END:
                break
            answer.append(new_token)
            walker = new_token
        return ' '.join(answer)

    def speech(self, text):
        if not text:
            text = self.talk()
        
        filtered_text = self.filter(text)
        return self.manager.text_to_speech(filtered_text)

    def choose_sticker(self):
        try:
            return random.choice(self.stickers)
        except:
            return ""

    def choose_animation(self):
        try:
            return random.choice(self.animations)
        except:
            return ""

    def choose_audio(self, text=None):
        try:
            return self.speech(text)
        except:
            return ""

    def set_torrent(self, new_level):
        if new_level >= 0 and new_level <= 10:
            self.torrent_level = new_level

    def get_torrent(self):
        return self.torrent_level

    def enable_learning(self):
        self.is_learning = True

    def disable_learning(self):
        self.is_learning = False

    def is_empty(self):
        return len(self.model) == 1

    def halve(self):
        for word in self.model:
            length = len(self.model[word])
            if length != 0:
                self.model[word] = self.model[word][length//2:] + [END]
        length = len(self.stickers)
        self.stickers = self.stickers[length//2:]
        length = len(self.animations)
        self.animations = self.animations[length//2:]

    def clean(self):
        # find words that are not referenced by any other word: those can be deleted safely
        words = set(self.model.keys())
        referenced_words = { BEGIN }
        for word in words:
            for successor in self.model[word]:
                referenced_words.add(successor)
                referenced_words.add(self.filter(successor))
        to_remove = words - referenced_words
        del words, referenced_words
        # there are many unreferenced words: among them, we delete only those with no successors except for END
        not_to_remove = set()
        for word in to_remove:
            successors = set(self.model[word]) - { END }
            if len(successors) != 0:
                not_to_remove.add(word)
                not_to_remove.add(self.filter(word))
        to_remove = to_remove - not_to_remove
        del not_to_remove
        # delete lonely words
        for word in to_remove:
            del self.model[word]
        del to_remove

    def flag(self, item, unique_id):
        self.stickers = list(filter(lambda sticker: sticker != item and not sticker.endswith(unique_id), self.stickers))
        self.animations = list(filter(lambda animation: animation != item and not animation.endswith(unique_id), self.animations))
        self.flagged_media.add(unique_id)

    def unflag(self, unique_id):
        if unique_id in self.flagged_media:
            self.flagged_media.remove(unique_id)

    def set_restricted_mode(self, restricted_mode):
        self.restricted_mode = restricted_mode

    def get_restricted_mode(self):
        return self.restricted_mode

    def filter(self, word):
        if type(word) != type(''):
            return word
        return ''.join(filter(lambda ch: ch.isalnum(), word)).lower()

    def __str__(self):
        jsonification = {"torrent_level": self.torrent_level,
                         "is_learning": self.is_learning,
                         "model": self.model,
                         "stickers": self.stickers,
                         "animations": self.animations,
                         "flagged_media": list(self.flagged_media),
                         "last_update": self.last_update,
                         "restricted_mode": self.restricted_mode}
        return json.dumps(jsonification)
