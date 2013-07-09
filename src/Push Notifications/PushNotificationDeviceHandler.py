#
# PushNotificationDeviceHandler.py
# Little Hedgehog Server
#
# Created by James Barrow on 04/07/2013.
#

#!/usr/bin/env python

import MySQLdb, time, binascii

username = ''		# Database username
password = ''		# Database password
dbName = ''		# Database name
portNum = 3306	# Port Number
dbTable = ''		# Table Name

def connectToDatabase():
	return MySQLdb.connect(host = "localhost", user = username, passwd = password, db = dbName, port = portNum)

def getDevice(db, token):
	db.query("SELECT * FROM %s WHERE token='%s'" %(dbTable, token))
	result = db.store_result()
	resultsTuple = result.fetch_row(0, 1)

	try:
		result = resultsTuple[0]
	except:
		result = None

	return result

def saveDevice(db, token, OSVersion, isDev):
	timestamp = int(time.time())
	db.query("INSERT INTO %s (token, badge, OSVersion, isDev, createdAt, updatedAt) VALUES ('%s', 0, '%s', '%d', '%d', '%d')" %(dbTable, token, OSVersion, isDev, timestamp, timestamp))

def updateDevice(db, token, badge, OSVersion, isDev, userInfo):
	timestamp = int(time.time())
	db.query("UPDATE %s SET badge = '%d', OSVersion = '%s', isDev = '%d', userInfo = '%s', updatedAt = '%s' WHERE token='%s'" %(dbTable, badge, OSVersion, isDev, userInfo, timestamp, token))

def deleteDevice(db, token):
	db.query("DELETE FROM %s WHERE token='%s'" %(dbTable, token))

def incrementBadge(token):
	db = connectToDatabase()

	device = getDevice(db, token)
	if device is not None:
		badge = device['badge']
		if badge <= 0:
			badge = 1
		else:
			badge += 1

		updateDevice(db, token, badge, device['OSVersion'], device['isDev'], device['userInfo'])
	else:
		badge = 1

	db.close()

	return badge

def resetBadge(token):
	db = connectToDatabase()
	db.query("UPDATE %s SET badge='0' WHERE token='%s'" % (dbTable, token))
	db.close()

def removeFeedbackDevice(feedbackTuple):
	db = connectToDatabase()
	token = binascii.hexlify(feedbackTuple[2])
	deviceDict = getDevice(db, token)
	if deviceDict is not None:
		if feedbackTuple[0] >= deviceDict['updatedAt']:
			deleteDevice(db, token)
	db.close()
