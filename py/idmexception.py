# -*- coding: utf-8 -*-

class IDMException(Exception):
	""" Custom exceptions for internal error checking.
	"""
	
	def __init__(self, message, status_code=400):
		self.status_code = status_code
		super().__init__(message)
	
