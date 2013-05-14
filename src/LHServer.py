#!/usr/bin/env python
import sys, json, ConfigParser
import MySQLdb
from datetime import datetime
from twisted.internet import reactor, stdio
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols import basic
from LHServerKeys import *

debug = True

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
	# elif line == 'broadcast'

	elif line == 'help' or line == '?':
		helpLog()

def stopServer():
	log("Stopping LHServer")
	sys.stdout.write("\r")
	sys.stdout.flush()
	reactor.stop()

def onlineClients():
	log("Online clients: %s" % factory.clients)

def onlineUsers():
	log("Online users: %s" % factory.users)

def broadcastServerChat(chat):
	log(chat)
	chatDict = {kChat:chat, kTimestamp:timestamp() + ' GMT', kChatType:kServerChat}

	for client in factory.clients:
		if client.username in factory.users:
			client.broadcast(chatDict, kChatBroadcast)

def helpLog():
	log("stop	 - Stops the server")
	log("clients	 - Shows current clients")
	log("online	 - Shows online users")
	log("help/?	 - Displays this help")

def log(message):
	if message != "":
		sys.stdout.write("\r")
		sys.stdout.flush()
		logString = "%s [LHEServer] %s" % (timestamp(), message)
		print logString

def timestamp():
	now = datetime.now()
	return now.strftime(TIMESTAMP_FORMAT)

# Class for setting up custom Twisted Factory object
class LHServerFactory(Factory):
	def __init__(self):
		self.clients = []
		self.users = {}
		self.protocol = LHServerProtocol
	
	def broadcastChat(self, chatDict, command):
		for client in self.clients:
			if client.username in self.users:
				client.broadcast(chatDict, command)
	
	def broadcastUserList(self):
		for client in self.clients:
			if client.username in self.users:
				client.broadcast(self.users, kUserList)

# Class for setting up custom Twisted Protocol object
class LHServerProtocol(Protocol):
	def __init__(self):
		self.username = ''

	def connectionMade(self):
		self.factory.clients.append(self)
		if debug:
			log("Client connected: %s" % self)

	def connectionLost(self, reason):
		try:
			self.factory.clients.remove(self)
		except :
			pass

		logoutUser(self, self.username)
		if debug:
			log("Client disconnected: %s" % self)

	def dataReceived(self, data):
		clientDict = {}
		loginPass = False
		try:
			jsonDict = json.loads(data)
		except ValueError as e:
			log(e)
			return
		command = jsonDict[kCommand]
		if debug:
			log("Command: " + command)

		if command:
			data = jsonDict[kData]

			if command == kChatBroadcast:
				self.factory.broadcastChat(data, kChatBroadcast)
			elif command == kStartType:
				self.factory.broadcastChat(data, kStartType)
			elif command == kEndType:
				self.broadcastChat(data, kEndType)
			elif command == kLogin:
				usr = str(data[kUsername]).lower()
				pswd = str(data[kPassword])
				loginPass = loginUserFromDatabase(usr, pswd)

				if loginPass:
					self.username = usr

					del loginPass[kPassword]

					try:
						clientDict = self.factory.users[self.username]
					except:
						pass

					self.broadcast(True, kLoginResponse)

					if clientDict == {}:
						clientDict = loginPass
						clientDict[kClientCount] = 1
						broadcastServerChat("%s has joined" % self.username)
					else:
						clientDict[kClientCount] = clientDict[kClientCount] +1

				else:
					self.broadcast(False, kLoginResponse)
			elif command == kLogout:
				logoutUser(self, str(data))

		if clientDict:
			self.factory.users[self.username] = clientDict

		if command == kLogin and loginPass:
			self.factory.broadcastUserList()

	def broadcast(self, message, command):
		tempDict = {kCommand:command, kData: message}
		jsonString = json.dumps(tempDict)
		if debug:
			log("JSON string: %s" % jsonString)
		self.transport.write(jsonString + '\r\n')

def loginUserFromDatabase(usr, pswd):
	db = MySQLdb.connect(host = "localhost", user = dbUsername, passwd = dbPassword, db = dbName, port = 3306)
	db.query("SELECT * FROM users WHERE username='%s' AND password = '%s'" % (usr, pswd))
	result = db.store_result()
	data = result.fetch_row(0, 1)
	db.close()

	if len(data) == 1:
		return data[0]
	else:
		return False

	log("Database result: %s" % str(data))

def logoutUser(client, usr):
	clientDict = {}
	try:
		clientDict = factory.users[client.username]
	except:
		pass
	finally:
		if clientDict != {}:
			clientDict[kClientCount] = clientDict[kClientCount] -1
			if clientDict[kClientCount] <= 0:
				try:
					del factory.users[usr]
				except:
					pass
				finally:
					factory.broadcastUserList()
					broadcastServerChat("%s has left" % usr)
					client.broadcast(True, kLogoutResponse)

if __name__ == '__main__':
	config=ConfigParser.ConfigParser()
	if config.read(['config.txt']):
		port = config.getint(kProperties, 'port')
		dbUsername = config.get(kProperties, 'dbUsername')
		dbPassword = config.get(kProperties, 'dbPassword')
		dbName = config.get(kProperties, 'dbName')

		stdio.StandardIO(Echo())
		factory = LHServerFactory()
		reactor.listenTCP(port, factory)
		log("LHServer started")
		reactor.run()
	else:
		log("No config.txt file found! Ending LHServer")
