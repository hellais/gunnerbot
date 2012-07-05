import re
import random
from twisted.words.protocols import irc
from twisted.internet import protocol, defer

def get_random_word():
    f = open('gunnerwords.txt')
    lines = f.readlines()
    ret = random.choice(lines)
    f.close()
    return ret.strip()

class GunnerBot(irc.IRCClient):
    # Commands that are fuzzy matched in general context
    commands = {'organize': 'groups_divide'}

    # Commands that should be directed to the bot
    sub_commands = {'question:': 'agreement_scale'}
    _namescallback = {}

    def names(self, channel):
        channel = channel.lower()
        d = defer.Deferred()
        if channel not in self._namescallback:
            self._namescallback[channel] = ([], [])

        self._namescallback[channel][0].append(d)
        self.sendLine("NAMES %s" % channel)
        return d

    def irc_RPL_NAMREPLY(self, prefix, params):
        channel = params[2].lower()
        nicklist = params[3].split(' ')

        if channel not in self._namescallback:
            return

        n = self._namescallback[channel][1]
        n += nicklist

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        channel = params[1].lower()
        if channel not in self._namescallback:
            return

        callbacks, namelist = self._namescallback[channel]

        for cb in callbacks:
            cb.callback(namelist)

        del self._namescallback[channel]

    def _get_nickname(self):
        return self.factory.nickname
    nickname = property(_get_nickname)

    def signedOn(self):
        self.join(self.factory.channel)
        print "Signed on as %s." % (self.nickname,)

    def joined(self, channel):
        print "Joined %s." % (channel,)

    def groups_divide(self, nicklist, msg):
        modn = len(nicklist)/4 + 1
        phrase = "Let's divide into %s groups of 4" % modn
        self.msg(self.factory.channel, phrase)
        phrase = ""
        for i, nick in enumerate(nicklist):
            phrase += "%s %s, " % (i + 1 % modn, nick)
        self.msg(self.factory.channel, phrase)

    @staticmethod
    def agreement(question, nick):
        import sha
        digest = sha.sha(question.lower()).digest() + sha.sha(nick).digest()
        digest = sha.sha(digest).hexdigest()
        seed = int(digest[-8:], 16)
        r = random.Random(seed)
        return r.uniform(0, 100)

    def agreement_scale(self, nicklist, msg):
        question = msg.split("question:")[-1].strip()

        phrase = "The question is \"%s\". " % question
        phrase = "People that agree completely will go to that end of the room "
        phrase += "(100%), people that disagree on the other (0%). "
        self.msg(self.factory.channel, phrase)

        agreements = [(nick, self.agreement(question, nick)) for nick in nicklist]
        agreements.sort(key = lambda x: x[1], reverse=True)
        phrase = ", ".join("%s %.1f%%" % (nick, pct) for (nick, pct) in agreements)

        self.msg(self.factory.channel, phrase)

    def privmsg(self, user, channel, msg):
        if self.nickname in msg:
            for key in self.sub_commands.keys():
                if key in msg:
                    self.names(self.factory.channel).addCallback(getattr(self,
                        self.sub_commands.get(key)), msg)
                    return
            prefix = "%s: " % (user.split('!', 1)[0], )
            phrase = get_random_word()
            if "%s" in phrase:
                phrase = phrase % user.split('!', 1)[0]
            self.msg(self.factory.channel, prefix + phrase)
            print "Saying %s" % phrase

        for key in self.commands.keys():
            if key in msg:
                self.names(self.factory.channel).addCallback(getattr(self, self.commands.get(key)))


class GunnerBotFactory(protocol.ClientFactory):
    protocol = GunnerBot

    def __init__(self, channel, nickname='gunnerbot2'):
        self.channel = channel
        self.nickname = nickname

    def clientConnectionLost(self, connector, reason):
        print "Lost connection (%s), reconnecting." % (reason,)
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "Could not connect: %s" % (reason,)

import sys
from twisted.internet import reactor

if __name__ == "__main__":
    reactor.connectTCP('irc.oftc.net', 6667, GunnerBotFactory('#gunnerbot'))
    reactor.run()

