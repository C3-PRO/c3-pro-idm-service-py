# -*- coding: utf-8 -*-

import arrow
from flask_jwt import current_identity
from bson.objectid import ObjectId

from .jsondocument import jsondocument
from .idmexception import IDMException


class Audit(jsondocument.JSONDocument):
	
	def __init__(self, ident, json=None):
		""" Should have: "actor_id", "datetime" and "action". May have "actor"
		spelt-out.
		"""
		super().__init__(None, 'audit', json=json)
	
	def for_api(self):
		return super().for_api(omit=['_id', 'type', 'actor_id', 'document'])
	
	
	# MARK: - Auditing
	
	@classmethod
	def audit_event_now(cls, document_id, action):
		audit = cls(None)
		del audit._id
		audit.datetime = arrow.utcnow().isoformat()
		audit.document = document_id
		if current_identity:
			audit.actor_id = current_identity.id
		audit.action = action
		return audit
	
	
	# MARK: - Actor
	
	def lookup_actor(self, server, bucket=None):
		""" Assumes the `actor_id` property points towards a type "user"
		and substitutes the `actor` doc id with the user's username.
		"""
		if not self.actor and self.actor_id:
			try:
				usr = User.with_id(self.actor_id, server, bucket=bucket)
				self.actor = usr.username
			except Exception as e:
				pass
	
	
	# MARK: - Search
	
	@classmethod
	def find_for_doc_id_on(cls, doc_id, server, bucket=None):
		""" Find all "audit" documents for the given document.
		"""
		if not doc_id:
			return None
		if ObjectId.is_valid(doc_id):
			doc_id = ObjectId(doc_id)
		rslt = cls.find_on({'type': 'audit', 'document': doc_id}, server, bucket=bucket)
		return rslt if rslt and len(rslt) > 0 else None

from .user import User

