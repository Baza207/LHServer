import sys, json, ConfigParser
import MySQLdb
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
	def __init__(self):
		self.username = ''

	def connectionMade(self):
		self.factory.clients.append(self)
		log("Client connected: %s" % self)

	def connectionLost(self, reason):
		clientDict = {}

		if self.username != '':
			log("%s has left" % self.username)
		else
			log("Client has left")

		try:
			self.factory.clients.remove(self)
		except :
			pass

		log("Client disconnected: %s" % self)

	def dataReceived(self, data):
		clientDict = {}
		loginPass = False

		jsonDict = json.loads(data)
		command = jsonDict[kCommand]
		log("Command: " + command)

		if command:
			data = jsonDict[kData]

			try:
				clientDict = self.factory.users[self.username]
			except:
				log("%s has joined" % data[kUsername])

			if command == kGroupChat:
				broadcastChat(self, data, kGroupChat)
			elif command == kStartType:
				broadcastChat(self, data, kStartType)
			elif command == kEndType:
				broadcastChat(self, data, kEndType)
			elif command == kLogin:
				usr = str(data[kUsername])
				pswd = str(data[kPassword])
				loginPass = loginUserFromDatabase(usr, pswd)

				if loginPass:
					self.username = usr

		self.factory.users[self.username] = clientDict

		if command == kLogin and loginPass:
			broadcastUserList()

	def broadcast(self, message, command):
		tempDict = {kCommand:command, kData: message}
		jsonString = json.dumps(tempDict)
		self.transport.write(jsonString)

def broadcastUserList():
	users = factory.users

	for client in factory.clients:
		if client.username in factory.users:
			client.broadcast(users, kUserList)

def broadcastChat(client, chatDict, command):
	for client in factory.clients:
		if client.username in factory.users:
			client.broadcast(chatDict, command)

def loginUserFromDatabase(usr, pswd):
	db = MySQLdb.connect(host = "localhost", user = dbUsername, passwd = dbPassword, db = dbName, port = 3306)
	db.query("SELECT * FROM users WHERE username='%s' AND password = '%s'" % (usr, pswd))
	result = db.store_result()
	data = result.fetch_row(0, 1)
	db.close()

	if len(data) == 1:
		log("Loged in")
		return True
	else:
		log("Login failed")
		return False

	log("Database result: %s" % str(data))

def logoutUser(usr):
	try:
		del self.factory.users[usr]
	except:
		pass
	finally:
		broadcastUserList()

if __name__ == '__main__':
	config=ConfigParser.ConfigParser()
	config.read(['config.txt'])
	port = config.getint('Properties', 'port')

	stdio.StandardIO(Echo())
	factory = LHServerFactory()
	reactor.listenTCP(port, factory)
	log("Server started")
	reactor.run()
