#!/bin/bash

echo "Add account to manager"
curl -H 'Content-Type: application/json' http://localhost:5000/account/ -X POST -d $(cat UTC*) 
echo

echo "Show accounts in manager"
curl -H 'Content-Type: application/json' http://localhost:5000/account/
echo

echo "Show account detail"
curl -H 'Content-Type: application/json' http://localhost:5000/account/af63264ff89aa82b4d325477dbeedce3cf827552
echo

echo "Unlock account with invalid password"
curl -H 'Content-Type: application/json' http://localhost:5000/account/af63264ff89aa82b4d325477dbeedce3cf827552 -X POST -d '{ "password" : "invalid_password" }'
echo

echo "Unlock account with valid password"
curl -H 'Content-Type: application/json' http://localhost:5000/account/af63264ff89aa82b4d325477dbeedce3cf827552 -X POST -d '{ "password" : "default" }'
echo

echo "Sign a transaction"
curl -H 'Content-Type: application/json' http://localhost:5000/account/af63264ff89aa82b4d325477dbeedce3cf827552 -X PUT -d '{ 
	"to": "0xF0109fC8DF283027b6285cc889F5aA624EaC1F55",
	"value": 1000000000,
	"gas": 2000000,
	"gasPrice": 234567897654321,
	"nonce": 0,
	"chainId": 1 }'
echo
