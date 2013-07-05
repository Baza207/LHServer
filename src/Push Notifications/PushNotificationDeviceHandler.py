#
# PushNotificationDeviceHandler.py
# Little Hedgehog Server
#
# Created by James Barrow on 04/07/2013.
#

#!/usr/bin/env python

import MySQLdb, time

username = ''		# Database username
password = ''		# Database password
dbName = ''		# Database name
portNum = 0		# Port Number
dbTable = ''		# Table Name

def __connectToDatabase():
	return MySQLdb.connect(host = "localhost", user = username, passwd = password, db = dbName, port = portNum)

def getDevice(db, token):
	db.query("SELECT * FROM %s WHERE token='%s'" % (dbTable, token))
	result = db.store_result()
	resultsTurple = result.fetch_row(0, 1)
	result = resultsTurple[0]

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
	db = __connectToDatabase()

	device = getDevice(db, token)
	badge = device['badge']
	if badge <= 0:
		badge = 1
	else:
		badge += 1

	updateDevice(db, token, badge, device['OSVersion'], device['isDev'], device['userInfo'])
	db.close()

	return badge

def resetBadge(token):
	db = __connectToDatabase()
	db.query("UPDATE %s SET badge='0' WHERE token='%s'" % (dbTable, token))
	db.close()
