# -*- coding: utf-8 -*-

from datetime import datetime

from .jsondocument import jsondocument
from .idmexception import IDMException


class Link(jsondocument.JSONDocument):
	
	def __init__(self, js=None):
		super().__init__(None, 'link', js)
	
	
	# MARK: - Validation
	
	@classmethod
	def validate_json(cls, js):
		if js is None:
			raise Exception("No JSON provided")
		for key in ['sub']:
			if key not in js:
				raise Exception("JSON is missing the `{}` element".format(key))
	
	
	# MARK: - CRUD
	
	def safe_update_and_store_to(self, js, server, bucket):
		""" Takes data sent via the web and updates the receiver. Will audit.
		"""
		self.__class__.validate_json(js)
		if js['sub'] != self.sub:
			raise IDMException('The SSSID the link points to cannot be changed', 409)
		
		statuschange = None
		if 'linked_to' in js:
			if self.linked_to is None:
				js['linked_on'] = int(datetime.timestamp(datetime.utcnow()))
				statuschange = 'link to {}'.format(js['linked_to'])
			elif self.linked_to != js['linked_to']:
				raise IDMException('Cannot change an established link', 409)
		
		self.update_with(js)
		self.store_to(server, bucket, statuschange)
	
	def store_to(self, server, bucket=None, action=None):
		""" Override to simultaneously store an "audit" document when storing
		link documents.
		"""
		now = int(datetime.timestamp(datetime.utcnow()))
		actor = current_identity.id if current_identity is not None else None
		audit = jsondocument.JSONDocument(None, 'audit', {'actor': actor, 'epoch': now})
		if self.created is None:
			self.created = now
			audit.update_with({'action': 'create'})
		else:
			self.changed = now
			audit.update_with({'action': action or 'update'})
		super().store_to(server, bucket)
		audit.update_with({'document': self.id})
		audit.store_to(server, bucket)
	
	
	# MARK: - JWT
	
	def jwt(self):
		if self._jwt is not None:
			return self._jwt
		if self.exp is not None:
			raise IDMException('This link has an expiration date but no JWT, hence it is invalid', 500)
		# TODO: use _id as `jti`
		# TODO: determine `iss` and `aud`
		# TODO: pull name and bday from SSSID and use on `sub` and `birthdate`
		# TODO: add expiration date to `exp`
		# TODO: generate JWT and store to `_jwt`
		return 'HEADER.PAYLOAD.SIGNATURE'
	
	
	# MARK: - Search
	
	@classmethod
	def find_jti_on(cls, jti, server, bucket=None):
		if not jti:
			return None
		rslt = cls.find_on({'type': 'link', '_id': jti}, server, bucket)
		return rslt[0] if len(rslt) > 0 else None
	
