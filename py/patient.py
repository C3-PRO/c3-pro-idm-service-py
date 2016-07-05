# -*- coding: utf-8 -*-

from .jsondocument import jsondocument


class Patient(jsondocument.JSONDocument):
	
	def __init__(self, sssid, json=None):
		self.sssid = sssid
		super().__init__(None, 'patient', json)
	
	
	# MARK: - Search
	
	@classmethod
	def find_sssid_on(cls, sssid, server, bucket=None):
		if not sssid:
			return None
		return cls.find_on({'type': 'patient', 'sssid': sssid}, server, bucket)
