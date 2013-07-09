#
#	APNservice.py
#	Little Hedgehog Server
#
#	Created by James Barrow on 18/06/2013.
#

#!/usr/bin/env python

import ssl, json, socket, struct, binascii, time, thread, logging
import PushNotificationDeviceHandler as deviceHandler

debug = True
# Sets the APNs to sandbox (True) or live (False)
sandbox = True
# Certification names and/or locations
liveCert = ''
devCert = 'LHS_anps_dev.pem'

logFileHandler = '../log/LHS_APNservice.log'
logLevel = logging.WARNING

MAX_RETRY = 1
RETRY_STATUS_CODES = [1, 10]

class APNservice(object):
	def __init__(self):
		super(APNservice, self).__init__()
		self.__sock = None
		self.__currentID = 0
		self.__failedTuple = None
		self.__notifBinaryDict = {}
		self.__failedCounts = {}

		# Setup Logging
		logging.basicConfig(level=logLevel,
							   format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
							   filename=logFileHandler,
							   filemode='a')
		console = logging.StreamHandler()
		console.setLevel(logLevel)
		formatter = logging.Formatter('%(name)-12s %(levelname)-8s %(message)s')
		console.setFormatter(formatter)
		self.logger = logging.getLogger('LHS_APNservice')
		self.logger.addHandler(console)

	def __recv_data(self, bufferSize, callback):
		# Receive data from other clients connected to server
		while 1:
			try:
				data = self.__sock.recv(bufferSize)
			except:
				if debug:
					self.logger.warning("APNs closed connection, thread exiting.")
				thread.interrupt_main()	#Handle the case when server process terminates
				break

			if not data:
				if debug:
					self.logger.warning("APNs closed connection, thread exiting. No data.")
				thread.interrupt_main()	# Recv with no data, server closed connection
				break
			else:
				callback(data)

	def __openSocket(self, address, cert):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__sock = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_SSLv3, server_side=False, certfile=cert)
		self.__sock.settimeout(3)

		try:
			self.__sock.connect(address)
		except:
			self.logger.error("Failed to connect to socket!")
			exit()

		if debug:
			self.logger.info("Opened socket to: %s" %(str(address)))

	# Opens a socket connection to the APNs
	def __openAPNsConnection(self):
		cert = ''
		if sandbox:
			cert = devCert
			address = ('gateway.sandbox.push.apple.com', 2195)
		else:
			cert = liveCert
			address = ('gateway.push.apple.com', 2195)

		self.__openSocket(address, cert)

	# Open a socket connection to the Feedback server
	def __openFeedbackConnection(self):
		cert = ''
		if sandbox:
			cert = devCert
			address = ('feedback.sandbox.push.apple.com', 2196)
		else:
			cert = liveCert
			address = ('feedback.push.apple.com', 2196)

		self.__openSocket(address, cert)

	def __closeConnection(self):
		self.__sock.close()
		self.__sock = None
		if debug:
			self.logger.info("Connection Closed")

	def __resetNotifs(self):
		self.__currentID = 0
		self.__failedTuple = None

	def __clearFailedTuple(self):
		self.logger.info(self.__failedCounts)
		if self.__failedTuple[2] in self.__notifBinaryDict.keys():
			del self.__notifBinaryDict[self.__failedTuple[2]]

		if self.__failedTuple[2] in self.__failedCounts.keys():
			del self.__failedCounts[self.__failedTuple[2]]

		self.__failedTuple = None

	# Makes a notification to be sent
	def __makeNotification(self, id, token, alert, badge, sound, userInfo):
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

	def __sendNotifications(self):
		queueIDsList = self.__notifBinaryDict.keys()
		sentIDsList = []

		self.__openAPNsConnection()
		thread.start_new_thread(self.__recv_data, (6, self.__recivedAPNsError,))

		for notifID in queueIDsList:
			notif = self.__notifBinaryDict[notifID]
			numBytesWritten = self.__sock.send(notif)
			if debug:
				self.logger.info("Number of bytes written: %d" %(numBytesWritten))

			sentIDsList.append(notifID)

		try:
			while 1:
				continue
		except KeyboardInterrupt:
			if self.__failedTuple is None:
				self.__resetNotifs()
				self.__closeConnection()
			else:
				for notifID in sentIDsList:
					if notifID is not self.__failedTuple[2]:
						queueIDsList.remove(notifID)
					else:
						break

				sentIDsList = list(set(sentIDsList) - set(queueIDsList))
				if debug:
					self.logger.info("Queued IDs: " + repr(queueIDsList))
					self.logger.info("  Sent IDs: " + repr(sentIDsList))

				for notifIDs in sentIDsList:
					del self.__notifBinaryDict[notifIDs]

				sentIDsList = []

				# Remove errored notif if not 1 or 10
				if self.__failedTuple[1] in RETRY_STATUS_CODES:
					self.logger.warning("Failed ID: %d" % self.__failedTuple[2])
					if self.__failedTuple[2] in self.__failedCounts.keys():
						failedCount = self.__failedCounts[self.__failedTuple[2]]
						if failedCount <= MAX_RETRY:
							self.__failedCounts[self.__failedTuple[2]] = failedCount+1
							if debug:
								self.logger.info("Retry notification with ID: %d failed with status: %d" %(self.__failedTuple[2], self.__failedTuple[1]))
						else:
							if self.__failedTuple[2] in queueIDsList:
								queueIDsList.remove(self.__failedTuple[2])
							self.__clearFailedTuple()
					else:
						self.__failedCounts[self.__failedTuple[2]] = 1

				else:
					if debug:
						self.logger.warning("Notification with ID: %d failed with status: %d" %(self.__failedTuple[2], self.__failedTuple[1]))

					if self.__failedTuple[2] in queueIDsList:
						queueIDsList.remove(self.__failedTuple[2])
					self.__clearFailedTuple()

				if debug:
					self.logger.info("Notif Dict Keys: " + repr(self.__notifBinaryDict.keys()))

				self.__closeConnection()

				if len(queueIDsList) > 0:
					self.__sendNotifications()
		except:
			self.__resetNotifs()
			self.__closeConnection()

	def __recivedAPNsError(self, errorBinary):
		fmt = '!BBI'
		errorTuple = struct.unpack(fmt, errorBinary)

		self.__failedTuple = errorTuple

	def __recivedFeedback(self, feedbackBinary):
		numOfChunks= len(feedbackBinary)/38
		if len(feedbackBinary) % 38:
			numOfChunks += 1

		if debug:
			self.logger.info("Number of chunks: %d" %numOfChunks)
		feedbackTupleList = []

		if len(feedbackBinary) > 38:
			for i in xrange(numOfChunks):
				startPoint = i*38
				endPoint = startPoint + 38
				chunk = feedbackBinary[startPoint: endPoint]
				feedbackTuple = self.__unpackFeedbackTuple(chunk)
				# feedbackTuple[2] = binascii.hexlify(feedbackTuple[2])
				feedbackTupleList.append(feedbackTuple)
		else:
			feedbackTuple = self.__unpackFeedbackTuple(feedbackBinary)
			# feedbackTuple[2] = binascii.hexlify(feedbackTuple[2])
			feedbackTupleList.append(feedbackTuple)

		if debug:
			self.logger.info(feedbackTupleList)

		for feedbackTuple in feedbackTupleList:
			deviceHandler.removeFeedbackDevice(feedbackTuple)

	def __unpackFeedbackTuple(self, data):
		fmt = '!IH32s'
		feedbackTuple = struct.unpack(fmt, data)
		return feedbackTuple

	# Sends a alert in a Push Notification
	def queueNotifications(self, tokens, alert, sound):
		self.__resetNotifs()

		for token in tokens:
			if len(token) > 0:
				badge = deviceHandler.incrementBadge(token)
				notif = self.__makeNotification(self.__currentID, token, alert, badge, sound, None)
				self.__notifBinaryDict[self.__currentID] = notif
				self.__currentID += 1

		self.__sendNotifications()

	# Get feedback response from server
	def checkFeedbackService(self):
		self.__openFeedbackConnection()
		thread.start_new_thread(self.__recv_data, (4096, self.__recivedFeedback,))

		try:
			while 1:
				continue
		except:
			self.__closeConnection()

# Makes an alert dictionary/string to insert into the notification JSON in makeNotification:
def makeAlert(body, actionLocKey, locKey, locArgs, launchImage):
	alertDict = {}

	if actionLocKey is not None and len(actionLocKey) > 0:
		alertDict['action-loc-key'] = actionLocKey

	if locKey is not None and len(locKey) > 0:
		alertDict['loc-key'] = locKey

	if locArgs is not None and len(locArgs) > 0:
		alertDict['loc-args'] = locArgs

	if len(alertDict.keys()) <= 0:
		return body

	if launchImage is not None and len(launchImage) > 0:
		alertDict['launch-image'] = launchImage

	if 'loc-key' not in alertDict.keys() and body is not None and len(body) > 0:
		alertDict['body'] = body

	if actionLocKey is None or len(actionLocKey) <= 0:
		alertDict['action-loc-key'] = None

	return alertDict
