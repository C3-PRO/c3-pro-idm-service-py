# -*- coding: utf-8 -*-

import arrow

from .jsondocument import jsondocument
from .idmexception import IDMException


class Subject(jsondocument.JSONDocument):
	
	def __init__(self, sssid, json=None):
		self.sssid = sssid
		if json is not None:
			self.validate_json(json)
		super().__init__(None, 'subject', json)
	
	
	# MARK: - Validation
	
	def validate_json(self, js):
		""" Validates the JSON to be used to populate the instance. Will check
		for sssid, name, bday but WILL NOT COMPLAIN if the instance already has
		these attributes.
		"""
		if js is None:
			raise Exception("No JSON provided")
		
		# check for mandatory fields (unless the instance already has attr)
		for key in ['sssid', 'name', 'bday']:
			if getattr(self, key) is not None:
				continue
			if key not in js:
				raise IDMException("JSON is missing the `{}` element".format(key))
			if not js[key]:
				raise IDMException("The `{}` element is empty".format(key))
		
		# validate dates provided
		for key in ['bday', 'date_invited', 'date_consented', 'date_enrolled', 'date_withdrawn']:
			if not key in js:
				continue
			try:
				validated = arrow.get(js[key])
				if validated.year < 1900:
					raise IDMException("Birth years before 1900 are not valid, you provided {}".format(validated.year))
				if validated.year > 2100:
					raise IDMException("Birth years after 2100 are not valid, you provided {}".format(validated.year))
			except Exception as e:
				raise IDMException("The date for {} \"{}\" is not properly formatted".format(key, js[key]))
	
	
	# MARK: - CRUD
	
	def populate_with_links(self, server, bucket):
		links = Link.find_on({'type': 'link', 'sub': self.sssid}, server, bucket)
		if links is not None:
			for lnk in links:
				
				# link was cancelled: subject has withdrawn (use latest)
				if lnk.withdrawn_on:
					withdrawn = arrow.get(lnk.withdrawn_on)
					if self.date_withdrawn is not None:
						my_withdrawn = arrow.get(self.date_withdrawn)
						self.date_withdrawn = withdrawn.isoformat() if withdrawn > my_withdrawn else self.date_withdrawn
					else:
						self.date_withdrawn = withdrawn.isoformat()
				
				# not withdrawn, but linked: subject is enrolled (use earliest)
				elif lnk.linked_on:
					rolled = arrow.get(lnk.linked_on)
					if self.date_enrolled is not None:
						my_rolled = arrow.get(self.date_enrolled)
						self.date_enrolled = rolled.isoformat() if rolled < my_rolled else self.date_enrolled
					else:
						self.date_enrolled = rolled.isoformat()
	
	def safe_update_and_store_to(self, js, server, bucket):
		""" Takes data sent via the web and updates the receiver. Will check
		if dates change and use it as audit action.
		"""
		self.validate_json(js)
		if js['sssid'] != self.sssid:
			raise IDMException("SSSID cannot be changed", 409)
		if 'type' in js:
			del js['type']
		
		changed = []
		for key in js:
			existing = getattr(self, key)
			if key[5:] in ['invited', 'consented', 'enrolled', 'withdrawn']:
				if js[key] != existing:
					if existing is not None:
						raise IDMException("Subject has already been {}".format(key[5:]), 409)
					changed.append('{}: {}'.format(key[5:], js[key]))
			elif js[key] != existing:
				changed.append('{}: \"{}\"'.format(key, js[key]))
		statuschange = '; '.join(changed) if len(changed) > 0 else None
		
		self.update_with(js)
		self.store_to(server, bucket=bucket, action=statuschange)
	
	def store_to(self, server, bucket=None, action=None):
		""" Override to simultaneously store an "audit" document when storing
		subject documents.
		
		:parameter server: The Mongo server to use
		:parameter bucket: The bucket to use (optional)
		:parameter action: The action that led to this store; will be used as
		                   `action` in the audit log
		"""
		now = arrow.utcnow().isoformat()
		if self.created is None:
			self.created = now
			action = 'create'
		else:
			action = action or 'update'
		self.changed = now
		super().store_to(server, bucket=bucket)
		
		audit = Audit.audit_event_now(self.id, action)
		audit.store_to(server, bucket=bucket)
	
	def for_api(self):
		return super().for_api(omit=['_id', 'type'])
	
	
	# MARK: - Search
	
	@classmethod
	def find_sssid_on(cls, sssid, server, bucket=None):
		if not sssid:
			return None
		return cls.find_on({'type': 'subject', 'sssid': sssid}, server, bucket)
	
	@classmethod
	def search(cls, searchstring, server, bucket=None, skip=0, limit=50, sort=None, descending=False):
		dic = {'type': 'subject'}
		if searchstring:
			dic['$or'] = [
				{'sssid': {'$regex': '{}.*'.format(searchstring), '$options': 'i'}},
				{'name': {'$regex': '.*{}.*'.format(searchstring), '$options': 'i'}},
				{'bday': {'$regex': '{}.*'.format(searchstring)}},
			]
		return cls.find_on(dic, server, bucket=bucket, skip=skip, limit=limit, sort=sort, descending=descending)
	
	@classmethod
	def find_on(cls, dic, server, bucket=None, skip=0, limit=50, sort=None, descending=False):
		res = super().find_on(dic, server, bucket, skip, limit, sort, descending)
		if res is not None:
			for subj in res:
				subj.populate_with_links(server, bucket)
		return res
	
	# MARK: - Links
	
	def create_new_link(self, settings, server, bucket=None):
		""" Creates a link for the given subject. Will throw if the subject
		has not yet been consented.
		"""
		if not self.sssid:
			raise IDMException("Subject has no SSSID", 500)
		if not self.date_consented:
			raise IDMException("Subject has not yet been consented", 412)
		
		lnk = Link(None, json={
			'sub': self.sssid,
			'iss': settings.jwt['iss'],
			'aud': settings.jwt['aud'],
			'secret': settings.jwt['secret'],
			'algorithm': settings.jwt['algorithm']})
		del lnk._id   # auto-creates UUID; we rely on Mongo
		lnk.store_to(server, bucket)
		return lnk
	
	
	# MARK: - Audits
	
	def all_audits(self, server, bucket=None):
		""" Find all "audit" documents for this subject AND for all links
		belonging to this subject.
		
		TODO: this should definitely be a view.
		"""
		audits = Audit.find_for_doc_id_on(self._id, server, bucket=bucket)
		if audits is not None and len(audits) > 0:
			[a.lookup_actor(server, bucket=bucket) for a in audits]
		else:
			audits = []
		
		links = Link.find_for_sssid_on(self.sssid, server, bucket=bucket)
		if links is not None and len(links) > 0:
			for link in links:
				link_audits = Audit.find_for_doc_id_on(link._id, server, bucket=bucket)
				if link_audits is not None and len(link_audits) > 0:
					for a in link_audits:
						a.action = "[Link] {}".format(a.action)
						a.lookup_actor(server, bucket=bucket)
					audits.extend(link_audits)
		
		audits.sort(key=lambda k: str(k.datetime) or '1970-01-01')
		return audits if len(audits) > 0 else None

from .link import Link
from .audit import Audit

