#!/usr/bin/env python

import ssl, json, socket, struct, binascii

debug = True
# Sets the APNs to sandbox or live
sandbox = True
# Certification names and/or locations
liveCert = ''
devCert = ''

def openSocket(address, cert):
	s = socket.socket()
	sock = ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_SSLv3, certfile=cert)

	try:
		sock.connect(address)
	except:
		exit("Failed to connect to address: %s" % address)

	return sock

# Opens a socket connection to the APNs
def openAPNsConnection():
	cert = ''
	if sandbox:
		cert = devCert
		apns_address = ('gateway.sandbox.push.apple.com', 2195)
	else:
		cert = liveCert
		apns_address = ('gateway.push.apple.com', 2195)

	openSocket(apns_address, cert)

# Open a socket connection to the Feedback server
def openFeedbackConnection():
	cert = ''
	if sandbox:
		cert = devCert
		apns_address = ('feedback.sandbox.push.apple.com', 2196)
	else:
		cert = liveCert
		apns_address = ('feedback.push.apple.com', 2196)

	openSocket(apns_address, cert)

# Makes an alert dictionary/string to insert into the notification JSON in makeNotification:
def makeAlert(body, actionLocKey, locKey, locArgs, launchImage):
	alertDict = {}

	if actionLocKey is not None and len(actionLocKey) > 0:
		alertDict['action-loc-key'] = actionLocKey
	else:
		alertDict['action-loc-key'] = None

	if locKey is not None and len(locKey) > 0:
		alertDict['loc-key'] = locKey

	if locArgs is not None and len(locArgs) > 0:
		alertDict['loc-args'] = locArgs

	if launchImage is not None and len(launchImage) > 0:
		alertDict['launch-image'] = launchImage

	if len(alertDict) <= 0:
		return body

	return alertDict

# Makes a notification to be sent
def makeNotification(token, alert, badge, sound, userInfo):
	if badge is None:
		badge = 0

	if soundName is None or len(soundName) <= 0:
		soundName = 'default'

	payloadDict = {'aps': {'alert': alert, 'badge': badge, 'sound': sound}}
	if len(userInfo) > 0:
		payloadDict = dict(payloadDict.items() + userInfo.items())

	payloadJSON = json.dumps(payloadString)

	binaryToken = binascii.unhexlify(token)
	fmt = "!cH32sH{0:d}s".format(len(payloadJSON))
	cmd = '\x00'
	notif = struct.pack(fmt, cmd, len(binaryToken), binaryToken, len(payloadJSON), payloadJSON)

	return notif

# Sends a alert in a Push Notification
def sendNotifications(tokensArray, alert, sound):
	sock = openAPNsConnection()

	for token in tokensArray:
		if len(token) > 0:
			notif = makeNotification(token, alert, badge, sound)
			# TODO: Increment badge number for token in database
			sock.write(notif)
			# TODO: Work out if the notification was sent correctly, if not, stop and start again from the message that was not sent

	sock.shutdown(SHUT_RDWR)
	sock.close()

# Get feedback response from server
def sendFeedbackRequest():
	sock = openFeedbackConnection()

	# TODO: Get response from the Feedback server socket to get tokens no longer valid

	sock.shutdown(SHUT_RDWR)
	sock.close()

# def main():
# 	print makeAlert("Hello", None, None, None, None)

# if __name__ == '__main__':
# 	main()
