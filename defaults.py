# -*- coding: utf-8 -*-

# To override settings, create a file "settings.py", import this file, and
# override whatever you need overridden.

# Mongo Server; leave host/port/db at None for default localhost connection
mongo_server = {
	'host': None,
	'port': None,
	'db': None,
	'user': None,
	'password': None,
	'bucket': 'c3pro_idm',
}

# JWT
jwt = {
	'iss': 'https://idm.c3-pro.io/',
	'aud': 'https://idm.c3-pro.io/',
	'expiration_seconds': 3600,
	'secret': 'super-duper-secret',
	'algorithm': 'HS256',
}

