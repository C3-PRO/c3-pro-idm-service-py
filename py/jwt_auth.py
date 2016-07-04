# -*- coding: utf-8 -*-

from werkzeug.security import safe_str_cmp
from . import user as usr

users = [
	usr.User('pascal.pfiffner@childrens.harvard.edu', 'test'),
]

username_table = {u.username: u for u in users}


def authenticate(username, password):
	user = username_table.get(username, None)
	if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
		return user
	return None

def identity(payload):
	user_id = payload['identity']
	return username_table.get(user_id, None)
