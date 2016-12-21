# -*- coding: utf-8 -*-

import arrow
from flask_jwt import current_identity

from .jsondocument import jsondocument
from .idmexception import IDMException


class Subject(jsondocument.JSONDocument):
	
	def __init__(self, sssid, json=None):
		self.sssid = sssid
		super().__init__(None, 'subject', json)
	
	
	# MARK: - Validation
	
	@classmethod
	def validate_json(cls, js):
		if js is None:
			raise Exception("No JSON provided")
		for key in ['sssid', 'name', 'bday']:
			if key not in js:
				raise IDMException("JSON is missing the `{}` element".format(key))
			if not js[key]:
				raise IDMException("The `{}` element is empty".format(key))
		try:
			arrow.get(js['bday'])
		except Exception as e:
			raise IDMException("The birth date \"{}\" is not properly formatted".format(js['bday']))
		for key in ['date_invited', 'date_consented', 'date_enrolled', 'date_withdrawn']:
			if not key in js:
				continue
			try:
				arrow.get(js[key])   # TODO: this will allow anything arrow can parse, but should only be ISO date-time
			except Exception as e:
				raise IDMException("The date for {} \"{}\" is not properly formatted".format(key, js[key]))
	
	
	# MARK: - CRUD
	
	def mark_consented(self, server, bucket):
		if self.date_consented:
			raise IDMException("Subject has already been consented", 409)
		self.date_consented = arrow.utcnow().isoformat()
		statuschange = 'date_consented: null -> {}'.format(self.date_consented)
		#self.store_to(server, bucket, statuschange)
	
	def safe_update_and_store_to(self, js, server, bucket):
		""" Takes data sent via the web and updates the receiver. Will check
		if dates change and use it as audit action.
		"""
		self.__class__.validate_json(js)
		if js['sssid'] != self.sssid:
			raise IDMException("SSSID cannot be changed", 409)
		if 'type' in js:
			del js['type']
		
		changed = []
		for d in ['invited', 'consented', 'enrolled', 'withdrawn']:
			key = 'date_{}'.format(d)
			if key in js and js[key] != self.__attr__(key):
				changed.add('{}: {} -> {}'.format(key, self.__attr__(key), js[key]))
		statuschange = ';\n\t'.join(changed) if len(changed) > 0 else None
		
		self.update_with(js)
		self.store_to(server, bucket, statuschange)
	
	def store_to(self, server, bucket=None, action=None):
		""" Override to simultaneously store an "audit" document when storing
		subject documents.
		
		:parameter server: The Mongo server to use
		:parameter bucket: The bucket to use (optional)
		:parameter action: The action that led to this store; will be used as
		                   `action` in the audit log
		"""
		now = arrow.utcnow().isoformat()
		actor = current_identity.id if current_identity is not None else None
		doc = jsondocument.JSONDocument(None, 'audit', {'actor': actor, 'datetime': now})
		if self.created is None:
			self.created = now
			doc.update_with({'action': 'create'})
		else:
			self.changed = now
			doc.update_with({'action': action or 'update'})
		super().store_to(server, bucket)
		doc.update_with({'document': self.id})
		doc.store_to(server, bucket)
	
	def for_api(self):
		return super().for_api(omit=['_id', 'id'])
	
	
	# MARK: - Search
	
	@classmethod
	def find_sssid_on(cls, sssid, server, bucket=None):
		if not sssid:
			return None
		return cls.find_on({'type': 'subject', 'sssid': sssid}, server, bucket)
	
	
	# MARK: - Links
	
	def create_new_link(self, settings, server, bucket=None):
		""" Creates a link for the given subject. Will throw if the subject
		has not yet been consented.
		"""
		if not self.sssid:
			raise IDMException('Subject has no SSSID', 500)
		if not self.date_consented:
			raise IDMException('Subject has not yet been consented', 412)
		
		lnk = Link(None, json={
			'sub': self.sssid,
			'iss': settings.jwt['iss'],
			'aud': settings.jwt['aud'],
			'secret': settings.jwt['secret'],
			'algorithm': settings.jwt['algorithm']})
		del lnk._id   # auto-creates UUID; we rely on Mongo
		lnk.store_to(server, bucket)
		return lnk

from .link import Link


