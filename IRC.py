import socket, ssl
import threading
import re

class IRCClient:
    def eventHandler(self, event):
        def registerhandler(handler):
            if event in self.handlers:
                self.handlers[event].append(handler)
            else:
                self.handlers[event] = [handler]
            return handler
        return registerhandler


    def __enter__(self, encoding="UTF-8"):
        __init__(self, encoding)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        disconnect(self)

    def __init__(self, encoding="UTF-8"):
        self.active = False
        self.encoding = encoding
        self.handlers = {}
        self.channelUsers = {}
        self.activethread = threading.Thread(target=self.mainloop)

    def _send(self, msg):
        self.irc.send(bytes(msg + "\r\n", self.encoding))
    
    def _recv(self):
        return self.irc.recv(2048).decode(self.encoding)

    def connect(self, server, nick, port=6667, username=None, password=None, usessl=False):
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if usessl:
            self.irc = ssl.wrap_socket(sock = self.irc, ciphers = "ECDHE-RSA-AES128-GCM-SHA256")
        self.nick = nick
        self.irc.connect((server, port))
        if password:
            self._send("PASS {}".format(password))
        self._send("USER {0} {0} {0} {0}".format(username))
        self._send("NICK {}".format(nick))

        while "001" not in self._recv(): # Wait until we've actually joined the network
            pass

        # Connected!

        self.active = True
        self.activethread.start()

    def disconnect(self, msg=""):
        self.active = False
        self._send("QUIT {}".format(msg))
    
    def joinChan(self, chan):
        self._send("JOIN {}".format(chan))
    
    def sendMsg(self, to, msg, action = False):
        if action:
            self._send("PRIVMSG {} :\x01ACTION {}\x01".format(to, msg))
        else:
            self._send("PRIVMSG {} :{}".format(to, msg))

    def getUsers(self, chan):
        return self.channelUsers[chan]

    def mainloop(self):
        while self.active:
            try:
                ircmsg = self._recv()
                print(ircmsg)
                match = re.search(r"^PING (.+)$", ircmsg, re.MULTILINE) # Ping
                if match:
                    self._send("PONG {}".format(match.group(1)))


                match = re.search(r"^:(.*)!.* PRIVMSG (.*) :(?!\x01ACTION.*\x01)(.*)$", ircmsg, re.MULTILINE) # Privmsg (non-action)
                if match:
                    sender = match.group(1).strip()
                    target = match.group(2).strip()
                    message = match.group(3).strip()
                    if "msg" in self.handlers:
                        for handler in self.handlers["msg"]:
                            handler(target, sender, message, False)

                    if target.startswith("#") and "chanMsg" in self.handlers:
                        for handler in self.handlers["chanMsg"]:
                            handler(target, sender, message, False)
                    elif "privMsg" in self.handlers:
                        for handler in self.handlers["privMsg"]:
                            handler(sender, message, False)
            


                match = re.search(r"^:(.*)!.* PRIVMSG (.*) :\x01ACTION(.*)\x01$", ircmsg, re.MULTILINE) # Privmsg (action)
                if match:
                    sender = match.group(1).strip()
                    target = match.group(2).strip()
                    message = match.group(3).strip()

                    if "msg" in self.handlers:
                        for handler in self.handlers["msg"]:
                            handler(target, sender, message, False)

                    if target.startswith("#") and "chanMsg" in self.handlers:
                        for handler in self.handlers["chanMsg"]:
                            handler(target, sender, message, False)
                    elif "privMsg" in self.handlers:
                        for handler in self.handlers["privMsg"]:
                            handler(sender, message, False)

                match = re.search(r"^:.* 353 .* = (.*) :(.*)$", ircmsg, re.MULTILINE) # /NAMES list
                if match:
                    channel = match.group(1).strip()
                    users = match.group(2).strip()
                    self.channelUsers[channel] = users.split()


                match = re.search(r"^:(.+)!.* JOIN :(.+)$", ircmsg, re.MULTILINE) # Join
                if match:
                    user = match.group(1).strip()
                    if user != self.nick:
                        channel = match.group(2).strip()
                        self.channelUsers[channel].append(user)
                        if "join" in self.handlers:
                            for handler in self.handlers["join"]:
                                handler(user, channel)


                match = re.search(r"^:(.+)!.* (PART|KICK) ([^ ]+)(?: :(.*))?$", ircmsg, re.MULTILINE) # Part/Kick
                if match:
                    user = match.group(1).strip()
                    kick = match.group(2) == "KICK"
                    channel = match.group(3).strip()
                    reason = match.group(4).strip()
                    match = re.search(r"^(?:@|&|%|\+|)" + user + "$", "\n".join(self.channelUsers[channel]), re.MULTILINE)
                    self.channelUsers[channel].remove(match.group())
                    if "part" in self.handlers:
                        for handler in self.handlers["part"]:
                            handler(match.group(), channel, kick)
                    
            except Exception as e:
                print("Exception: " + str(e))
