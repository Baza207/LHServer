#!/usr/bin/env python
import unittest

import LHServer
import MySQLdb
import json
import time
from threading import Thread
from multiprocessing import Process
from telnetlib import Telnet

LHServer.debug = False

USERNAME = 'lhserver1'
PASSWORD = 'lhserver1'
DATABASE = 'LHServerTest1'
PORT = 25552

TEST_USER = 'testuser'
TEST_PASSWORD = 'testpassword'

class LoginTest(unittest.TestCase):
    
    def setUp(self):
        db = MySQLdb.connect(user=USERNAME, passwd=PASSWORD, db=DATABASE)
        db.query("SELECT * FROM users WHERE username='%s'" % TEST_USER)
        result = db.store_result()
        data = result.fetch_row(0, 1)
        if not data:
            db.query("INSERT INTO users (username, password) VALUES ('%s','%s')" % (TEST_USER, TEST_PASSWORD))
        else:
            db.query("UPDATE users SET password='%s' WHERE username='%s'" % (TEST_PASSWORD, TEST_USER))
        db.close()
    
    def testCorrectLogin(self):
        self.assertDictEqual({'username': TEST_USER, 'password': TEST_PASSWORD},
                             LHServer.loginUserFromDatabase(TEST_USER, TEST_PASSWORD))
        
    def testWrongLogin(self):
        self.assertFalse(LHServer.loginUserFromDatabase(TEST_USER, TEST_PASSWORD+'abc'))


class TelnetTest(unittest.TestCase):
    def setUp(self):
        try:
            self.telnetConnection = Telnet('localhost', PORT)
        except Exception as e:
            print 'Error connecting to LHServer'
            print 'ERROR', e
    
    def tearDown(self):
        try:
            self.telnetConnection.close()
        except Exception as e:
            print 'Error closing connection'
            print 'ERROR', e
    
    def testLoginLogout(self):
        # Login
        self.telnetConnection.write(json.dumps({
                "command":"login",
                "data":{"username":TEST_USER, "password":TEST_PASSWORD}
            }))
        line = self.telnetConnection.read_until('\n')
        self.assertDictEqual({"data": True, "command": "loginResponse"},
                             json.loads(line))
        
        # Get userList
        line = self.telnetConnection.read_until('\n')
        self.assertDictContainsSubset({"command": "userList"},
                                      json.loads(line))
        
        # Logout
        self.telnetConnection.write(json.dumps({
                "command":"logout",
                "data":TEST_USER
            }))
        line = self.telnetConnection.read_until('\n')
        self.assertDictEqual({"data": True, "command": "logoutResponse"},
                             json.loads(line))
        
    def testLoginFailed(self):
        self.telnetConnection.write(json.dumps({
                "command":"login",
                "data":{"username":TEST_USER, "password":TEST_PASSWORD+'abc'}
            }))
        line = self.telnetConnection.read_until('\n')
        self.assertDictEqual({"data": False, "command": "loginResponse"},
                             json.loads(line))
        
    def testIllegalCommand(self):
        self.telnetConnection.write('Just illegal data')
        line = self.telnetConnection.read_until('\n')
        self.assertDictContainsSubset({"command": "error"},
                                      json.loads(line))
        

if __name__ == '__main__':
    # Setup the LHServer
    LHServer.setup(username=USERNAME, password=PASSWORD, database=DATABASE, port=PORT)
    # Start the server
    reactor_process = Process(target=LHServer.reactor.run, kwargs={'installSignalHandlers':0})
    reactor_process.daemon = True
    reactor_process.start()
    # Run tests
    unittest.main()
    # Stop the server
    LHServer.stopServer()
    reactor_process.join()
