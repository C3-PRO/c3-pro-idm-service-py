# -*- coding: utf-8 -*-

import uuid
import arrow
import bcrypt
from bson import ObjectId

from .jsondocument import jsondocument
from .idmexception import IDMException


class User(jsondocument.JSONDocument):
	server = None
	bucket = None
	
	def __init__(self, username, password=None, json=None):
		self.username = username
		self.password = None
		self.admin = False
		if password is not None:
			self.set_password(password)
		super().__init__(None, 'user', json=json)
	
	def __str__(self):
		return "User(id='{}')".format(self.id)
	
	def set_password(self, password):
		assert password
		salt = bcrypt.gensalt()
		self.password = bcrypt.hashpw(password.encode('utf-8'), salt)   # would be nice to store the salt separately
		self.temporary = None
	
	
	# MARK: - Instance
	
	def temporary_pass_hash(self, server, bucket=None):
		tmp = self.temporary
		if tmp is not None:
			hsh = tmp.get('hash')
			tme = tmp.get('time')
			if hsh is not None and tme is not None:
				exp = arrow.get(tme)
				if exp is not None and exp > arrow.utcnow():
					return hsh
		
		self.create_temporary_pass(server, bucket)
		hsh = self.temporary.get('hash') if self.temporary is not None else None
		if hsh is None:
			raise IDMException("failed to create a temporary password link, please try again")
		return hsh
	
	def create_temporary_pass(self, server, bucket=None):
		self.temporary = {
			'hash': str(uuid.uuid4()),
			'time': arrow.utcnow().shift(hours=2).timestamp,
		}
		self.store_to(server, bucket, action='generate temporary password')
	
	def email_temporary_pass(self, mailer, link):
		text = "Dear {},\n\nPlease click the link below to set a new password:\n{}\n\nYou can reply to this email if you keep having issues logging in.\n\nBest regards,\nyour friendly IDM machine".format(self.username, link)
		mailer.send_mail(self.username, "C Tracker IDM Password Reset", text)
	
	@classmethod
	def reset_password_for(cls, pass_hash, pass1, pass2, server, bucket=None):
		res = cls.find_on({'type': 'user', 'temporary.hash': pass_hash}, server, bucket)
		if not res or 0 == len(res):
			raise IDMException("your password reset link is invalid, please request a new one by clicking “I forgot”")
		if not pass1 or len(pass1) < 8:
			raise IDMException("your password is too short")
		if not pass2 or pass1 != pass2:
			raise IDMException("passwords do not match")
		usr = res[0]
		exp = usr.temporary.get('time')
		if not exp or arrow.get(exp) < arrow.utcnow():
			raise IDMException("your password reset link has expired, please request a new one by clicking “I forgot”")
		usr.set_password(pass1)
		usr.store_to(server, bucket, action='reset password')
	
	def store_to(self, server, bucket=None, action=None):
		""" Override to simultaneously store an "audit" document when storing
		user documents.
		
		:parameter server: The Mongo server to use
		:parameter bucket: The bucket to use (optional)
		:parameter action: The action that led to this store; will be used as
		                   `action` in the audit log
		"""
		super().store_to(server, bucket=bucket)
		
		audit = Audit.audit_event_now(self.id, action or 'update')
		audit.store_to(server, bucket=bucket)
	
	def for_api(self):
		return super().for_api(omit=['_id', 'type', 'password'])

	
	# MARK: - Class Methods
	
	@classmethod
	def get(cls, username, server, bucket=None):
		""" Raises if the user does not exist.
		"""
		if not username:
			raise IDMException("you must provide a username")
		
		res = cls.find_on({'type': 'user', 'username': username}, server, bucket)
		if res and len(res) > 0:
			return res[0]
		raise IDMException("no user with the given username", 404)
	
	@classmethod
	def with_id(cls, user_id, server, bucket=None):
		""" Raises if the user does not exist.
		"""
		if ObjectId.is_valid(user_id):
			user_id = ObjectId(user_id)
		res = cls.find_on({'type': 'user', '_id': user_id}, server, bucket)
		if res and len(res) > 0:
			return res[0]
		raise IDMException("no user with the given id “{}”".format(user_id), 404)
	
	@classmethod
	def with_pass(cls, username, password, server, bucket=None):
		""" Raises if the user does not exist or if the password is wrong.
		"""
		if not password:
			raise IDMException("no password given")
		usr = cls.get(username, server, bucket)
		hashed = usr.password
		if hashed != bcrypt.hashpw(password.encode('utf-8'), hashed):
			raise IDMException("incorrect password")
		return usr
	
	@classmethod
	def create(cls, username, password, is_admin, server, bucket=None):
		if not username:
			raise IDMException("you must provide a username")
		if not password or len(password) < 8:
			raise IDMException("you must provide a password with at least 8 characters")
		
		# is the username already in use?
		res = cls.find_on({'type': 'user', 'username': username}, server, bucket)
		if res and len(res) > 0:
			raise IDMException("this username has already been taken", 409)
		
		# create user
		usr = cls(username, password)
		if is_admin:
			usr.admin = True
		del usr._id
		usr.store_to(server, bucket, action='create')
		return usr
	
	@classmethod
	def delete(cls, username, server, bucket=None):
		usr = cls.get(username, server, bucket)
		usr.remove_from(server, bucket)
	
	@classmethod
	def has_admins(cls, server, bucket=None):
		""" Checks whether there are any admins in the system.
		"""
		res = cls.find_on({'type': 'user', 'admin': True}, server, bucket)
		return True if res and len(res) > 0 else False

from .audit import Audit

