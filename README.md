## Little Hedgehog Server

The goal with this project is to make a multiplayer server base that will allow connections from a variety of different devices and authentications and to allow parts to be made, added and/or removed in a modular fashion. This is currently starting with making a basic chat server and expanding on that.

In the future the server will allow users to connect through different types of authentication, for example from a database (the current system), with Facebook, Twitter or GameCenter.

**NOTE**: This is currently in pre-alpha and not all features are implimented.

### Current Features
- Basic authentication of clients with database,  
- Sending messages from client to server,  
- Broadcasting group chat messages to all autenticated clients,  
- Broadcasting sever messages to clients.  

###Roadmap
Read the roadmap [here!](https://github.com/Baza207/LHServer/blob/master/ROADMAP.md)

## Prerequisites

LHServer is written on Python 2.6 with the following extra libraries:

- MySQLdb  
- Twisted

Users are stored in a MySQL database, the structure of which is described below.

## Database Structure

After creating a MySQL database, use the following to create the table structure:

```
CREATE TABLE `users` (
  `username` varchar(80) NOT NULL DEFAULT '',
  `password` varchar(40) NOT NULL DEFAULT '',
  PRIMARY KEY (`username`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
```

At the moment users have to be created manually in the database. Passwords are stored as SHA1 by the client.

## JSON Structure

### Base structure
#### Variables
- `command` -  The command string to be processed. This is always a string.
- `data` -		The data for the command. This can be any variable type but is normally a dictionary.


```
{
  "command" : " ",
  "data" : { }
}
```

For more details of the variables for each command, please refer to [`LHServerKeys.py`](https://github.com/Baza207/LHServer/blob/master/src/LHServerKeys.py) and [`tests.py`](https://github.com/Baza207/LHServer/blob/master/src/tests.py).

## Client Applications

Currently there are no publiacally avaliable client aplications.

## License

LHServer is available under the MIT license. See the LICENSE file for more info.

### Creator

[James Barrow - Pig on a Hill](http://pigonahill.com)  
[@PigonaHill](https://twitter.com/PigonaHill)
