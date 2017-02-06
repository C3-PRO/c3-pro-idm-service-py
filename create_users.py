#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
import requests


print("Login with your IDM admin username and password. Press CTRL + C to abort.")
host = input("IDM Host [localhost:9096]: ")
if not host:
	host = "http://localhost:9096"
token = None

# log in
while not token:
	try:
		username = input("Admin username: ")
		password = getpass.getpass("Admin password: ")
		
		# get token
		res = requests.post(host+'/auth', json={'username': username, 'password': password})
		res.raise_for_status()
		js = res.json()
		token = js.get('access_token')
	except Exception as e:
		print("Failed: {}".format(e))

# create user
abort = False
while not abort:
	print()
	print("Create a new user")
	
	newname = input("Username (email address): ")
	newpass = getpass.getpass("Password: ")
	isadmin = input("Is this an admin user? [y/N]: ")
	
	# create user
	try:
		data = {'username': newname, 'password': newpass}
		if isadmin and 'y' == isadmin[:1].lower():
			data['admin'] = True
		res = requests.post(host+'/user', json=data, headers={'Authorization': 'JWT {}'.format(token)})
		res.raise_for_status()
		print("Added")
		
		nextone = input("Add another user? [y/N]: ")
		if not nextone or 'n' == nextone[:1].lower():
			abort = True
	except Exception as e:
		print("Failed: {}".format(e))

print("Done")
