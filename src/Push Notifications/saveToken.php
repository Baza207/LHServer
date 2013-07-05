<?php
//
//	saveToken.php
//	Little Hedgehog Server
//
//	Created by James Barrow on 02/07/2013.
//

	include "../config.php";

	function getTokenFromDB($dbTable, $token)
	{
		$query = "SELECT * FROM $dbTable WHERE token='$token'";
		$queryResult = mysql_query($query);

		$results = array();
		while ($row = mysql_fetch_array($queryResult))
		{
			array_push($results, $row);
		}

		if (count($results) > 0)
		{
			return $results[0];
		}
		else
		{
			return NULL;
		}
	}

	function saveToken($dbTable, $token, $userInfo, $OSVersion, $isDev)
	{
		$timestamp = time();

		$query = "INSERT INTO $dbTable (token, userInfo, badge, OSVersion, isDev, createdAt, updatedAt) VALUES ('$token', '$userInfo', 0, '$OSVersion', '$isDev', '$timestamp', '$timestamp')";
		mysql_query($query);

		print "Saved new token\n";
	}

	function updateToken($dbTable, $result, $token, $userInfo)
	{
		$query = "UPDATE $dbTable SET badge=0 WHERE token='$token'";
		mysql_query($query);

		// This needs to be expanded to see if any row has been updated!
		if($result["userInfo"] != $userInfo)
		{
			$timestamp = time();

			$query = "UPDATE $dbTable SET userInfo='$userInfo', updatedAt='$timestamp' WHERE token='$token'";
			mysql_query($query);

			print "Updated token and reset badge\n";
		}
		else
		{
			print "Reset badge, no need to update token\n";
		}
	}

	function deleteToken($dbTable, $token)
	{
		$query = "DELETE FROM $dbTable WHERE token='$token'";
		mysql_query($query);

		print "Deleted token\n";
	}

	$http_verb = strtolower($_SERVER['REQUEST_METHOD']) or die("Unable to get http verb!\n");

	print(strtoupper($http_verb) . "\n");

	switch ($http_verb)
	{
		case "post":
		{
			$token = $_POST[token];
			$userInfo = $_POST[userInfo];
			$OSVersion = $_POST[OSVersion];
			$isDev = $_POST[isDev];

			mysql_connect("localhost", $username, $password);
			@mysql_select_db($database) or die("Unable to select database!\n");

			$tokenResult = getTokenFromDB($dbTable, $token);
			print("Token Result: " . $tokenResult . "\n");

			if ($tokenResult)
			{
				// Update an existing token
				print("Updating...\n");
				updateToken($dbTable, $tokenResult, $token, $userInfo);
			}
			else
			{
				// A new token to add
				print("Saving...\n");
				saveToken($dbTable, $token, $userInfo, $OSVersion, $isDev);
			}

			mysql_close();
			break;
		}

		case "delete":
		{
			$token = $_SERVER[QUERY_STRING];

			mysql_connect("localhost", $username, $password);
			@mysql_select_db($database) or die("Unable to select database!\n");

			print("Token to delete: " . $token . "\n");
			// Delete a token
			deleteToken($dbTable, $token);

			mysql_close();
			break;
		}

		default:
		{
			print(strtoupper($http_verb) . " is an unused verb!\n");
			break;
		}
	}
?>
