# -*- coding: utf-8 -*-

from . import user as user


def authenticate(username, password):
	""" This function is called when making a request to the /auth endpoint.
	"""
	try:
		return user.User.with_pass(username, password, user.server, user.bucket)
	except Exception as e:
		return None

def identity(payload):
	user_id = payload.get('identity')
	return user.User.with_id(user_id, user.server, user.bucket)
