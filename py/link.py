# -*- coding: utf-8 -*-

import jwt
import arrow
from flask_jwt import current_identity
from bson.objectid import ObjectId

from .jsondocument import jsondocument
from .idmexception import IDMException


class Link(jsondocument.JSONDocument):
	
	def __init__(self, ident, json=None):
		if 'algorithm' not in json:
			json['algorithm'] = 'HS256'
		for key in ['sub', 'iss', 'aud', 'secret', 'algorithm']:
			if key not in json or not json[key]:
				raise IDMException("The value for `{}` can not be empty".format(key), 400)
		super().__init__(None, 'link', json=json)
	
	
	# MARK: - Validation
	
	def validate_json(self, js):
		if js is None:
			raise Exception("No JSON provided")
	
	
	# MARK: - Linking
	
	@classmethod
	def link_jwt_to_fhir_patient(cls, in_jwt, patient, server, bucket=None):
		""" Attempts to find the link represented by the given JWT, then
		attempts to establish the link.
		"""
		lnk = cls.find_jwt_on(in_jwt, server, bucket)
		if lnk is None:
			raise IDMException('Forbidden', 403)
		lnk.link_to_fhir_patient(patient, server, bucket)
	
	def link_to_fhir_patient(self, patient, server, bucket=None):
		""" Expects a FHIR JSON Patient resource and will forward to
		`safe_update_and_store_to()` appropriately.
		
		If handed a JWT, use the `link_jwt_to_fhir_patient()` class method
		instead.
		"""
		if self.linked_to:
			raise IDMException("this link has already been established", 409)
		if not self.exp or arrow.get(self.exp) < arrow.utcnow():
			raise IDMException("this link has expired", 403)
		if patient is None or not isinstance(patient, dict) or 'resourceType' not in patient or 'Patient' != patient['resourceType']:
			raise IDMException("you must provide a FHIR `Patient` resource", 406)
		idents = patient.get('identifier', {})
		ident = idents[0] if list == type(idents) and len(idents) > 0 else {}
		sys = ident.get('system')
		val = ident.get('value')
		if not val:
			raise IDMException("you must provide a value in the Patient resource's first `identifier` element", 406)
		
		js = {'linked_to': val}
		if sys:
			js['linked_system'] = sys
		self.safe_update_and_store_to(js, server, bucket=bucket)
	
	def safe_update_and_store_to(self, js, server, bucket=None):
		""" Takes data sent via the web and updates the receiver. Will audit.
		"""
		self.validate_json(js)
		if self._jwt is not None:
			for key in ['sub', 'iss', 'aud', 'exp', 'secret', 'algorithm']:
				if key in js and js[key] != getattr(self, key):
					raise IDMException("property `{}` can no longer be changed".format(key), 409)
		if 'type' in js:
			del js['type']
		if 'linked_on' in js:
			del js['linked_on']
		
		statuschange = None
		if 'linked_to' in js:
			if self.linked_to is None:
				js['linked_on'] = arrow.utcnow().isoformat()
				statuschange = 'link to {}'.format(js['linked_to'])
			else:
				if self.linked_to != js['linked_to']:
					raise IDMException("cannot change an established link [1]", 409)
				if 'linked_system' in js and self.linked_system != js['linked_system']:
					raise IDMException("cannot change an established link [2]", 409)
		elif 'linked_system' in js:
			raise IDMException("cannot set `linked_system` without `linked_to`")
		
		self.update_with(js)
		self.store_to(server, bucket, statuschange)
	
	
	# MARK: - JWT
	
	def jwt(self, server, bucket=None):
		if self._jwt is not None:
			return self._jwt
		if self.exp is not None:
			raise IDMException("this link has an expiration date but no JWT, hence it is invalid", 500)
		
		# retrieve subject
		res = Subject.find_sssid_on(self.sub, server, bucket)
		if res is None or len(res) < 1:
			raise IDMException("the subject to this link does not exist", 404)
		
		# generate and store JWT
		self.exp = arrow.utcnow().shift(hours=24).timestamp
		payload = {
			'jti': self._id,
			'iss': self.iss,
			'aud': self.aud,
			'exp': self.exp,
			'sub': res[0].name,       # pull name and bday from SSSID and use on `sub` and `birthdate`
			'birthdate': res[0].bday,
		}
		self._jwt = jwt.encode(payload, self.secret, algorithm=self.algorithm)
		self.store_to(server, bucket, 'create JWT')
		return self._jwt
	
	
	# MARK: - CRUD
	
	def store_to(self, server, bucket=None, action=None):
		""" Override to simultaneously store an "audit" document when storing
		link documents.
		"""
		now = arrow.utcnow().timestamp
		actor = current_identity.id if current_identity else None
		audit = jsondocument.JSONDocument(None, 'audit', {'actor': actor, 'epoch': now})
		del audit._id
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
		return super().for_api(omit=['secret', '_jwt'])
	
	
	# MARK: - Search
	
	@classmethod
	def find_jti_on(cls, jti, server, bucket=None):
		if not jti:
			return None
		if ObjectId.is_valid(jti):
			jti = ObjectId(jti)
		rslt = cls.find_on({'_id': jti}, server, bucket)
		return rslt[0] if len(rslt) > 0 else None
	
	@classmethod
	def find_jwt_on(cls, jwt, server, bucket=None):
		if not jwt:
			return None
		rslt = cls.find_on({'type': 'link', '_jwt': bytes(jwt, encoding='utf-8')}, server, bucket)
		return rslt[0] if len(rslt) > 0 else None
	
	@classmethod
	def find_for_sssid_on(cls, sssid, server, bucket=None):
		if not sssid:
			return None
		rslt = cls.find_on({'type': 'link', 'sub': sssid}, server, bucket)
		return rslt if len(rslt) > 0 else None

from .subject import Subject

