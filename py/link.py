# -*- coding: utf-8 -*-

import jwt
from flask_jwt import current_identity
from datetime import datetime, timedelta
from bson.objectid import ObjectId

from .jsondocument import jsondocument
from .idmexception import IDMException
from .subject import Subject


class Link(jsondocument.JSONDocument):
	
	def __init__(self, ident, json=None):
		if 'algorithm' not in json:
			json['algorithm'] = 'HS256'
		for key in ['sub', 'iss', 'aud', 'secret', 'algorithm']:
			if key not in json or not json[key]:
				raise IDMException("The value for `{}` can not be empty".format(key), 400)
		super().__init__(None, 'link', json=json)
	
	
	# MARK: - Validation
	
	@classmethod
	def validate_json(cls, js):
		if js is None:
			raise Exception("No JSON provided")
	
	
	# MARK: - CRUD
	
	def safe_update_and_store_to(self, js, server, bucket):
		""" Takes data sent via the web and updates the receiver. Will audit.
		"""
		self.__class__.validate_json(js)
		if self._jwt is not None:
			for key in ['sub', 'iss', 'aud', 'exp', 'secret', 'algorithm']:
				if key in js and js[key] != getattr(self, key):
					raise IDMException("The `{}` can no longer be changed".format(key), 409)
		if 'type' in js:
			del js['type']
		
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
	
	def for_api(self):
		return super().for_api(omit=['secret'])
	
	
	# MARK: - JWT
	
	def jwt(self, server, bucket=None):
		if self._jwt is not None:
			return self._jwt
		if self.exp is not None:
			raise IDMException("This link has an expiration date but no JWT, hence it is invalid", 500)
		
		# retrieve subject
		res = Subject.find_sssid_on(self.sub, server, bucket)
		if res is None or len(res) < 1:
			raise IDMException("The subject to this link does not exist", 404)
		
		# generate and store JWT
		self.exp = datetime.utcnow() + timedelta(hours=24)
		payload = {
			'jti': self._id,
			'iss': self.iss,
			'aud': self.aud,
			'exp': self.exp,
			'sub': res[0].name,       # pull name and bday from SSSID and use on `sub` and `birthdate`
			'birthdate': res[0].bday,
		}
		j = jwt.encode(payload, self.secret, algorithm=self.algorithm)
		# TODO: generate JWT and store to `_jwt`, also store `exp`
		return j
	
	
	# MARK: - Search
	
	@classmethod
	def find_jti_on(cls, jti, server, bucket=None):
		if not jti:
			return None
		rslt = cls.find_on({'_id': ObjectId(jti)}, server, bucket)
		return rslt[0] if len(rslt) > 0 else None
	
