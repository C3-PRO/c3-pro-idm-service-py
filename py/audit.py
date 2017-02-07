# -*- coding: utf-8 -*-

import arrow
from bson.objectid import ObjectId

from .jsondocument import jsondocument
from .idmexception import IDMException


class Audit(jsondocument.JSONDocument):
	
	def __init__(self, ident, json=None):
		super().__init__(None, 'audit', json=json)
	
	def for_api(self):
		if self.datetime:
			self.datetime = arrow.get(self.datetime).isoformat()
		return super().for_api(omit=['_id', 'type'])
	
	
	# MARK: - Search
	
	@classmethod
	def find_for_doc_id_on(cls, doc_id, server, bucket=None):
		if not doc_id:
			return None
		if ObjectId.is_valid(doc_id):
			doc_id = ObjectId(doc_id)
		rslt = cls.find_on({'type': 'audit', 'document': doc_id}, server, bucket)
		if not rslt or 0 == len(rslt):
			return None
		
		# fetch names of the users
		# TODO: this should be a view!
		for doc in rslt:
			actor = doc.actor
			if actor:
				try:
					usr = User.with_id(actor, server, bucket=bucket)
					doc.actor = usr.username
				except Exception as e:
					doc.actor = "Unknown Actor"
		return rslt

from .user import User

