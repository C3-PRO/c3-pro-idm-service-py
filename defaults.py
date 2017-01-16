# -*- coding: utf-8 -*-

# To override settings, create a file "settings.py", import this file, and
# override whatever you need overridden.

# Admin's email address - also used on password reset emails
admin_email = 'webmaster@c3-pro-idm.org'

# Mongo Server; leave host/port/db at None for default localhost connection
mongo_server = {
	'host': None,
	'port': None,
	'db': None,
	'user': None,
	'password': None,
	'bucket': 'c3pro_idm',
}

# Settings for the JWT to be issued to the app
jwt = {
	'iss': 'https://idm.c3-pro.io/',
	'aud': 'https://idm.c3-pro.io/',
	'expiration_seconds': 43200,
	'secret': 'super-duper-secret',
	'algorithm': 'HS256',
}

