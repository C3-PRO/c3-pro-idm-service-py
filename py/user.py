# -*- coding: utf-8 -*-


class User(object):
	def __init__(self, username, password):
		self.id = username
		self.username = username
		self.password = password
	
	def __str__(self):
		return "User(id={})".format(self.id)

