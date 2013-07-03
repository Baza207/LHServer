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

def recv_data(sock, bufferSize):
	# Receive data from other clients connected to server
	while 1:
		try:
			recv_data = sock.recv(bufferSize)
		except:
			print "APNs closed connection, thread exiting."
			thread.interrupt_main()	#Handle the case when server process terminates
			break

		if not recv_data:
			print "APNs closed connection, thread exiting. No data."
			thread.interrupt_main()	# Recv with no data, server closed connection
			break
		else:
			print "Received data: " + str(recv_data)
			fmt = '!BBI'
			print struct.unpack(fmt, recv_data)
			thread.interrupt_main()
			break

def openSocket(address, cert):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_SSLv3, server_side=False, certfile=cert)
	sock.settimeout(3)

	try:
		sock.connect(address)
	except:
		exit("Failed to connect to socket!")

	print "Opened socket to: %s" %(str(address))

	return sock

# Opens a socket connection to the APNs
def openAPNsConnection():
	cert = ''
	if sandbox:
		cert = devCert
		address = ('gateway.sandbox.push.apple.com', 2195)
	else:
		cert = liveCert
		address = ('gateway.push.apple.com', 2195)

	return openSocket(address, cert)

# Open a socket connection to the Feedback server
def openFeedbackConnection():
	cert = ''
	if sandbox:
		cert = devCert
		address = ('feedback.sandbox.push.apple.com', 2196)
	else:
		cert = liveCert
		address = ('feedback.push.apple.com', 2196)

	return openSocket(address, cert)

def closeConnection(sock):
	sock.shutdown(socket.SHUT_WR)
	sock.close()
	if debug:
		print "Connection Closed"

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

	if len(alertDict) <= 0:
		return body

	if actionLocKey is None or len(actionLocKey) <= 0:
		alertDict['action-loc-key'] = None

	return alertDict

# Makes a notification to be sent
def makeNotification(token, alert, badge, sound, userInfo):
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

	if debug:
		print ("ID for notification is: %s" % timestamp)

	fmt = '!BIIH32sH%ds' %(len(payloadJSON))
	cmd = 1
	notif = struct.pack(fmt, cmd, timestamp, expiry, len(binaryToken), binaryToken, len(payloadJSON), payloadJSON)

	return notif

# Sends a alert in a Push Notification
def sendNotifications(tokens, alert, sound):
	sock = openAPNsConnection()

	thread.start_new_thread(recv_data, (sock, 6,))

	for token in tokens:
		if len(token) > 0:
			badge = 1 # TODO: Increment badge number for token in database
			notif = makeNotification(token, alert, badge, sound, None)

			nBytesWritten = sock.send(notif)
			if debug:
				print "nBytesWritten: %d" %(nBytesWritten)

	try:
		while 1:
			continue
	except:
		closeConnection(sock)


# Get feedback response from server
def checkFeedbackService():
	sock = openFeedbackConnection()

	# TODO: Get response from the Feedback server socket to get tokens no longer valid
	data = sock.recv(1024)
	print "Data recived: %s" %(data)

	if len(data) > 0:
		fmt = '!IH32s'
		feedbackTuples = struct.unpack(fmt, data)

		if debug:
			print feedbackTuples

	closeConnection(sock)
