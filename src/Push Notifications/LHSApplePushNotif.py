#
#	LHSApplePushNotif.py
#	Little Hedgehog Server
#
#	Created by James Barrow on 18/06/2013.
#

#!/usr/bin/env python

import ssl, json, socket, struct, binascii, time, thread

debug = True
# Sets the APNs to sandbox or live
sandbox = True
# Certification names and/or locations
liveCert = ''
devCert = 'LHS_anps_dev.pem'

MAX_RETRY = 1
RETRY_STATUS_CODES = [1, 10]

class LHSAPNclient(object):
	def __init__(self):
		super(LHSAPNclient, self).__init__()
		self.sock = None
		self.currentID = 0
		self.failedTurple = None
		self.notifBinaryDict = {}
		self.failedCounts = {}


	def recv_data(self, bufferSize, callback):
		# Receive data from other clients connected to server
		while 1:
			try:
				data = self.sock.recv(bufferSize)
			except:
				if debug:
					print "APNs closed connection, thread exiting."
				thread.interrupt_main()	#Handle the case when server process terminates
				break

			if not data:
				if debug:
					print "APNs closed connection, thread exiting. No data."
				thread.interrupt_main()	# Recv with no data, server closed connection
				break
			else:
				callback(data)
				thread.interrupt_main()
				break

	def openSocket(self, address, cert):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_SSLv3, server_side=False, certfile=cert)
		self.sock.settimeout(3)

		try:
			self.sock.connect(address)
		except:
			exit("Failed to connect to socket!")

		if debug:
			print "Opened socket to: %s" %(str(address))

	# Opens a socket connection to the APNs
	def openAPNsConnection(self):
		cert = ''
		if sandbox:
			cert = devCert
			address = ('gateway.sandbox.push.apple.com', 2195)
		else:
			cert = liveCert
			address = ('gateway.push.apple.com', 2195)

		self.openSocket(address, cert)

	# Open a socket connection to the Feedback server
	def openFeedbackConnection(self):
		cert = ''
		if sandbox:
			cert = devCert
			address = ('feedback.sandbox.push.apple.com', 2196)
		else:
			cert = liveCert
			address = ('feedback.push.apple.com', 2196)

		self.openSocket(address, cert)

	def closeConnection(self):
		# self.sock.shutdown(socket.SHUT_WR)
		self.sock.close()
		self.sock = None
		if debug:
			print "Connection Closed"

	def resetNotifs(self):
		self.currentID = 0
		self.failedTurple = None

	def clearFailedTurple(self):
		print self.failedCounts
		if self.failedTurple[2] in self.notifBinaryDict.keys():
			del self.notifBinaryDict[self.failedTurple[2]]

		if self.failedTurple[2] in self.failedCounts.keys():
			del self.failedCounts[self.failedTurple[2]]

		self.failedTurple = None

	# Makes a notification to be sent
	def makeNotification(self, id, token, alert, badge, sound, userInfo):
		if badge is None:
			badge = 0

		if sound is None or len(soundName) <= 0:
			sound = 'default'

		payloadDict = {'aps': {'alert': alert, 'badge': badge, 'sound': sound}}
		if userInfo is not None and len(userInfo) > 0:
			payloadDict = dict(payloadDict.items() + userInfo.items())

		payloadJSON = json.dumps(payloadDict)
		binaryToken = binascii.unhexlify(token)
		timestamp = int(time.time())
		expiry = timestamp + 86400

		fmt = '!BIIH32sH%ds' %(len(payloadJSON))
		cmd = 1
		notif = struct.pack(fmt, cmd, id, expiry, len(binaryToken), binaryToken, len(payloadJSON), payloadJSON)

		return notif

	# Sends a alert in a Push Notification
	def queueNotifications(self, tokens, alert, sound):
		self.resetNotifs()

		for token in tokens:
			if len(token) > 0:
				badge = 1 # TODO: Increment badge number for token in database
				notif = self.makeNotification(self.currentID, token, alert, badge, sound, None)
				self.notifBinaryDict[self.currentID] = notif
				self.currentID += 1

		self.sendNotifications()

	def sendNotifications(self):
		queueIDsList = self.notifBinaryDict.keys()
		sentIDsList = []

		self.openAPNsConnection()
		thread.start_new_thread(self.recv_data, (6, self.recivedAPNsError,))

		for notifID in queueIDsList:
			notif = self.notifBinaryDict[notifID]
			numBytesWritten = self.sock.send(notif)
			if debug:
				print "Number of bytes written: %d" %(numBytesWritten)

			sentIDsList.append(notifID)

		try:
			while 1:
				continue
		except KeyboardInterrupt:
			if self.failedTurple is None:
				self.resetNotifs()
				self.closeConnection()
			else:
				for notifID in sentIDsList:
					if notifID is not self.failedTurple[2]:
						queueIDsList.remove(notifID)
					else:
						break

				sentIDsList = list(set(sentIDsList) - set(queueIDsList))
				if debug:
					print "Queued IDs: " + repr(queueIDsList)
					print "  Sent IDs: " + repr(sentIDsList)

				for notifIDs in sentIDsList:
					del self.notifBinaryDict[notifIDs]

				sentIDsList = []

				# Remove errored notif if not 1 or 10
				if self.failedTurple[1] in RETRY_STATUS_CODES:
					print "Failed ID: %d" % self.failedTurple[2]
					if self.failedTurple[2] in self.failedCounts.keys():
						failedCount = self.failedCounts[self.failedTurple[2]]
						if failedCount <= MAX_RETRY:
							self.failedCounts[self.failedTurple[2]] = failedCount+1
							if debug:
								print "Retry notification with ID: %d failed with status: %d" % (self.failedTurple[2], self.failedTurple[1])
						else:
							if self.failedTurple[2] in queueIDsList:
								queueIDsList.remove(self.failedTurple[2])
							self.clearFailedTurple()
					else:
						self.failedCounts[self.failedTurple[2]] = 1

				else:
					if debug:
						print "Notification with ID: %d failed with status: %d" % (self.failedTurple[2], self.failedTurple[1])

					if self.failedTurple[2] in queueIDsList:
						queueIDsList.remove(self.failedTurple[2])
					self.clearFailedTurple()

				if debug:
					print "Notif Dict Keys: " + repr(self.notifBinaryDict.keys())

				self.closeConnection()

				if len(queueIDsList) > 0:
					self.sendNotifications()
		except:
			self.resetNotifs()
			self.closeConnection()

	def recivedAPNsError(self, errorBinary):
		fmt = '!BBI'
		errorTurple = struct.unpack(fmt, errorBinary)

		if debug:
			print errorTurple

		self.failedTurple = errorTurple

	# Get feedback response from server
	def checkFeedbackService(self):
		self.openFeedbackConnection()
		thread.start_new_thread(self.recv_data, (1024, self.recivedFeedbackError,))
		closeConnection()

	def recivedFeedbackError(self, errorBinary):
		fmt = '!IH32s'
		feedbackTuples = struct.unpack(fmt, data)

		if debug:
			print feedbackTuples

# Makes an alert dictionary/string to insert into the notification JSON in makeNotification:
def makeAlert(body, actionLocKey, locKey, locArgs, launchImage):
	alertDict = {}

	if actionLocKey is not None and len(actionLocKey) > 0:
		alertDict['action-loc-key'] = actionLocKey

	if locKey is not None and len(locKey) > 0:
		alertDict['loc-key'] = locKey

	if locArgs is not None and len(locArgs) > 0:
		alertDict['loc-args'] = locArgs

	if launchImage is not None and len(launchImage) > 0:
		alertDict['launch-image'] = launchImage

	if len(alertDict.keys()) <= 0:
		return body

	if 'loc-key' not in alertDict.keys() and body is not None and len(body) > 0:
		alertDict['body'] = body

	if actionLocKey is None or len(actionLocKey) <= 0:
		alertDict['action-loc-key'] = None

	return alertDict
