from IRC import IRCClient
import sys
import signal

irc = IRCClient()
irc.connect(server="tinet.org.uk", port=6697, nick="TestBot", usessl=True)
irc.joinChan("#bots")

def close(signum, frame):
    irc.disconnect()
    sys.exit(0)


signal.signal(signal.SIGINT, close)

@irc.eventHandler("privMsg")
def onMsg(sender, message, action):
    if not action: # The message was not a /me (action) one
        irc.sendMsg(sender, irc.getUsers("#bots")) # Send back a list of all users in #bots

while True:
    pass
