import sys, json, ConfigParser
from datetime import datetime
from twisted.internet import reactor, stdio
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols import basic
from LHServerKeys import *

# Class for getting input from the console
class Echo(basic.LineReceiver):
	from os import linesep as delimiter

	def lineReceived(self, line):
		consoleInput(line)

def consoleInput(line):
	if line == 'stop':
		stopServer()
	elif line == 'clients':
		onlineClients()
	elif line == 'online':
		onlineUsers()
	elif line == 'help' or line == '?':
		helpLog()

def stopServer():
	log("Stopping server")
	sys.stdout.write("\r")
	sys.stdout.flush()
	reactor.stop()

def onlineClients():
	log("Online clients: %s" % factory.clients)

def onlineUsers():
	log("Online users: %s" % factory.users)

def helpLog():
	log("stop	 - Stops the server")
	log("clients	 - Shows current clients")
	log("online	 - Shows online users")
	log("help	 - Displays this help")

def log(message):
	if message != "":
		sys.stdout.write("\r")
		sys.stdout.flush()
		logString = "%s [LHEServer] %s" % (timestamp(), message)
		print logString

def timestamp():
	now = datetime.now()
	return now.strftime("%Y-%m-%d %H:%M:%S")

# Class for setting up custom Twisted Factory object
class LHServerFactory(Factory):
	def __init__(self):
		self.clients = []
		self.users = {}
		self.protocol = LHServerProtocol

# Class for setting up custom Twisted Protocol object
class LHServerProtocol(Protocol):
	def connectionMade(self):
		self.factory.clients.append(self)
		# log("Client connected: %s" % hash(self))

	def connectionLost(self, reason):
		clientDict = {}
		try:
			clientDict = self.factory.users[hash(self)]
		except:
			pass
		finally:
			log("%s has left" % clientDict[kName])

		try:
			del self.factory.users[hash(self)]
		except:
			pass
		finally:
			self.factory.clients.remove(self)
			broadcastUserList()

		# log("Client disconnected: %s" % hash(self))

	def dataReceived(self, data):
		clientDict = {}

		jsonDict = json.loads(data)
		command = jsonDict[kCommand]
		# log("Command: " + command)

		if command:
			data = jsonDict[kData]
			uuid = jsonDict[kUUID]

			if command == kGroupChat:
				broadcastChat(self, data)
			elif command == kRegister:
				try:
					clientDict = self.factory.users[hash(self)]
				except:
					log("%s has joined" % data[kName])
				clientDict[kUUID] = uuid
				clientDict[kName] = data[kName]

		self.factory.users[hash(self)] = clientDict

		if command == kRegister:
			broadcastUserList()

	def broadcast(self, message, command):
		tempDict = {kCommand:command, kData: message}
		jsonString = json.dumps(tempDict)
		self.transport.write(jsonString)

def broadcastUserList():
	users = factory.users

	for client in factory.clients:
		if hash(client) in factory.users:
			client.broadcast(users, kUserList)

def broadcastChat(client, chatDict):
	for client in factory.clients:
		if hash(client) in factory.users:
			client.broadcast(chatDict, kGroupChat)

if __name__ == '__main__':
	config=ConfigParser.ConfigParser()
	config.read(['config.txt'])
	port = config.getint('Properties', 'port')

	stdio.StandardIO(Echo())
	factory = LHServerFactory()
	reactor.listenTCP(port, factory)
	log("Server started")
	reactor.run()
