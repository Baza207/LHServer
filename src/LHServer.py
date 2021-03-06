#
#	LHServer.py
#	Little Hedgehog Server
#
#	Created by James Barrow on 29/05/2013.
#

#!/usr/bin/env python

import sys, json, ConfigParser
import MySQLdb
from datetime import datetime
from twisted.internet import reactor, stdio
from twisted.internet.protocol import Factory, Protocol
from twisted.protocols import basic

debug = True
TIMESTAMP_FORMAT	= '%d/%m/%Y %H:%M:%S'

def stopServer():
	if debug:
		log("Stopping LHServer")

	sys.stdout.flush()
	reactor.stop()

def onlineClients():
	log("Online clients: %s" % factory.clients)

def onlineUsers():
	log("Online users: %s" % factory.users)

def broadcastServerChat(*args):
	chat = ' '.join(args)
	if debug:
		log(chat)

	chatDict = {'chat':chat, 'timestamp':timestamp() + ' GMT', 'chatType':'serverChat'}

	for client in factory.clients:
		if client.username in factory.users:
			client.broadcast(chatDict, 'chatBroadcast', 1)

def helpLog():
	'''Print help message'''
	log("stop            - Stops the server")
	log("clients         - Shows current clients")
	log("online          - Shows online users")
	log("broadcast msg   - Send a message to every client")
	log("help/?          - Displays this help")


class Echo(basic.LineReceiver):
	'''Class for getting input from the console'''
	from os import linesep as delimiter

	command_list = {
			'stop': stopServer,
			'clients': onlineClients,
			'online': onlineUsers,
			'help': helpLog,
			'?': helpLog,
			'broadcast': broadcastServerChat
		}

	def lineReceived(self, line):
		args = line.split(' ')
		cmd = args.pop(0)
		if self.command_list.has_key(cmd):
			# Call the function with the rest as arguments
			try:
				self.command_list[cmd](*args)
			except TypeError as e:
				log(e)
		else:
			log('Invalid command "%s"' % line)

def log(message):
	'''Basic logging to stdout'''
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
	'''Server object'''
	def __init__(self):
		self.clients = []
		self.users = {}

	def buildProtocol(self, addr):
		return LHServerProtocol(self)

	def broadcastChat(self, chatDict, command):
		for client in self.clients:
			if client.username in self.users:
				client.broadcast(chatDict, command, 0)

	def broadcastUserList(self):
		for client in self.clients:
			if client.username in self.users:
				client.broadcast({'users':self.users}, 'userList', 0)

# Class for setting up custom Twisted Protocol object
class LHServerProtocol(Protocol):
	'''Client object'''
	def __init__(self, factory):
		self.username = ''
		self.factory = factory

	def connectionMade(self):
		'''Called when a connection is made.'''
		self.factory.clients.append(self)
		if debug:
			log("Client connected: %s" % self)

	def connectionLost(self, reason):
		'''Called when the connection is shut down.'''
		try:
			self.factory.clients.remove(self)
		except :
			pass

		logoutUser(self, self.username)
		if debug:
			log("Client disconnected: %s" % self)

	def dataReceived(self, data):
		'''Called whenever data is received.'''
		clientDict = {}
		loginPass = False
		try:
			jsonDict = json.loads(data)
		except ValueError as e:
			if debug:
				log(e)
			self.broadcast({'error_description':'Illegal command'}, 'error', -1)
			return

		command = jsonDict['command']
		if debug:
			log("Command: " + command)

		if command:
			data = jsonDict['data']

			if command == 'chatBroadcast':
				self.factory.broadcastChat(data, 'chatBroadcast')
			elif command == 'startType':
				self.factory.broadcastChat(data, 'startType')
			elif command == 'endType':
				self.broadcastChat(data, 'endType')
			elif command == 'login':
				usr = str(data['username']).lower()
				pswd = str(data['password'])
				loginPass = loginUserFromDatabase(usr, pswd)

				if loginPass:
					self.username = usr

					del loginPass['password']

					try:
						clientDict = self.factory.users[self.username]
					except:
						pass

					self.broadcast({'response_success':True}, 'loginResponse', 1)

					if clientDict == {}:
						clientDict = loginPass
						clientDict['clientCount'] = 1
						if debug:
							broadcastServerChat("%s has joined" % self.username)
					else:
						clientDict['clientCount'] = clientDict['clientCount'] +1

				else:
					self.broadcast({'response_success':False}, 'loginResponse', -1)
			elif command == 'logout':
				logoutUser(self, str(data))

		if clientDict:
			self.factory.users[self.username] = clientDict

		if command == 'login' and loginPass:
			self.factory.broadcastUserList()

	def broadcast(self, message, command, status):
		'''Send message to client'''
		tempDict = {'command':command, 'data': message}
		jsonString = json.dumps(tempDict)
		if debug:
			log("JSON string: %s" % jsonString)
		self.transport.write(jsonString + '\r\n')

def loginUserFromDatabase(usr, pswd):
	'''Basic authentication'''
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
			clientDict['clientCount'] = clientDict['clientCount'] -1
			if clientDict['clientCount'] <= 0:
				try:
					del factory.users[usr]
				except:
					pass
				finally:
					broadcastServerChat("%s has left" % usr)
					client.broadcast({'response_success':True}, 'logoutResponse', 1)
					factory.broadcastUserList()

def setup(username, password, database, port=25552):
	global dbUsername, dbPassword, dbName, factory
	dbUsername = username
	dbPassword = password
	dbName = database
	factory = LHServerFactory()
	reactor.listenTCP(port, factory)

def startServer():
	reactor.run()

if __name__ == '__main__':
	defaults = {'port': '25552',
				'dbUsername':'',
				'dbPassword':'',
				'dbName':''}

	# config.txt settings
	config=ConfigParser.ConfigParser(defaults)
	if config.read(['config.txt']):
		defaults = dict(config.items("Properties"))

	# Command line settings
	try:
		# For python2.6 this will not work by default
		import argparse
		parser = argparse.ArgumentParser()
		# Use the configparser's settings as defaults
		parser.set_defaults(**defaults)
		parser.add_argument("--port", "-P",
					help="Port to listen to, defaults to 25552", dest='port')
		parser.add_argument("--username", "-u",
					help="The username", dest='dbusername')
		parser.add_argument("--password", "-p",
					help="The password", dest='dbpassword')
		parser.add_argument("--db", "-d", help="Database", dest='dbname')
		args = parser.parse_args()

		port = int(args.port)
		dbUsername = args.dbusername
		dbPassword = args.dbpassword
		dbName = args.dbname
	except Exception as e:
		print 'ERROR',e
		# argparse not found
		print defaults
		port = int(defaults['port'])
		dbUsername = defaults['dbusername']
		dbPassword = defaults['dbpassword']
		dbName = defaults['dbname']

	stdio.StandardIO(Echo())
	setup(port=port, username=dbUsername, password=dbPassword, database=dbName)
	log("LHServer started on port %i" % port)
	startServer()
