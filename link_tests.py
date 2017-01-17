#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import arrow
import unittest
from py import link
from py.idmexception import IDMException
from py.jsondocument import mockserver as mock


class LinkTests(unittest.TestCase):
	
	def testSafeUpdating(self):
		srv = mock.MockServer()
		lnk = link.Link(None, doc_unlinked)
		
		# JWT generated, can no longer change these:
		for key in ['sub', 'iss', 'aud', 'exp', 'secret', 'algorithm']:
			with self.assertRaises(IDMException) as cm:
				lnk.safe_update_and_store_to({key: 'xyz'}, srv)
			self.assertEqual(cm.exception.status_code, 409)
		
		# cannot change linked_system alone
		with self.assertRaises(IDMException) as cm:
			lnk.safe_update_and_store_to({'linked_system': 'xyz'}, srv)
		self.assertEqual(cm.exception.status_code, 400)
		
		# cannot change linked_to afterwards
		lnk.safe_update_and_store_to({'linked_to': 'A1', 'linked_system': 'org.c3-pro'}, srv)
		with self.assertRaises(IDMException) as cm:
			lnk.safe_update_and_store_to({'linked_to': 'B2'}, srv)
		self.assertEqual(cm.exception.status_code, 409)
		with self.assertRaises(IDMException) as cm:
			lnk.safe_update_and_store_to({'linked_to': 'A1', 'linked_system': 'ch.c-tracker'}, srv)
		self.assertEqual(cm.exception.status_code, 409)
	
	def testEstablishing(self):
		srv = mock.MockServer()
		lnk = link.Link(None, doc_unlinked)
		
		# link expired
		lnk.exp = arrow.utcnow().shift(hours=-2).timestamp
		with self.assertRaises(IDMException) as cm:
			lnk.link_to_fhir_patient({'resourceType': 'Patient', 'identifier': [{'value': 'abc'}]}, srv)
		self.assertEqual(cm.exception.status_code, 403)
		lnk.exp = arrow.utcnow().shift(hours=2).timestamp
		
		# successful link
		lnk.link_to_fhir_patient({'resourceType': 'Patient', 'identifier': [{'system': 'org.c3-pro', 'value': 'abc'}]}, srv)
		
		# can not link a second time
		with self.assertRaises(IDMException) as cm:
			lnk.link_to_fhir_patient({'resourceType': 'Patient', 'identifier': [{'value': 'abc'}]}, srv)
		self.assertEqual(cm.exception.status_code, 409)
	
	def testEstablishingFull(self):
		srv = mock.MockServer()
		srv.found_documents = [doc_unlinked]
		
		# missing patient
		with self.assertRaises(IDMException) as cm:
			link.Link.link_jwt_to_fhir_patient("xxx", None, srv)
		self.assertEqual(cm.exception.status_code, 406)
		
		# no FHIR resourceType
		with self.assertRaises(IDMException) as cm:
			link.Link.link_jwt_to_fhir_patient("xxx", {}, srv)
		self.assertEqual(cm.exception.status_code, 406)
		
		# no identifier
		with self.assertRaises(IDMException) as cm:
			link.Link.link_jwt_to_fhir_patient("xxx", {'resourceType': 'Patient'}, srv)
		self.assertEqual(cm.exception.status_code, 406)
		
		# no value in identifier
		with self.assertRaises(IDMException) as cm:
			link.Link.link_jwt_to_fhir_patient("xxx", {'resourceType': 'Patient', 'identifier': [{'system': 'org.c3-pro'}]}, srv)
		self.assertEqual(cm.exception.status_code, 406)
		
		# successful linking (method does round-trip to server, hence can apparently link multiple times)
		link.Link.link_jwt_to_fhir_patient("xxx", {'resourceType': 'Patient', 'identifier': [{'system': 'org.c3-pro', 'value': 'abc'}]}, srv)
		link.Link.link_jwt_to_fhir_patient("xxx", {'resourceType': 'Patient', 'identifier': [{'value': 'abc'}]}, srv)
	
	def testAlreadyEstablished(self):
		srv = mock.MockServer()
		srv.found_documents = [doc_linked]
		
		with self.assertRaises(IDMException) as cm:
			link.Link.link_jwt_to_fhir_patient("xxx", {}, srv)
		self.assertEqual(cm.exception.status_code, 409)
		

doc_unlinked = { "_id": "587de98ad55ab68b60e98897", "secret": "super-duper-secret", "algorithm": "HS256", "created": 1484646794, "changed": 1484646794, "_jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2lkbS5jMy1wcm8uaW8vIiwiZXhwIjoxNDg0NzMyODg1LCJzdWIiOiJCcnVubyBNYXJzIiwiYXVkIjoiaHR0cHM6Ly9pZG0uYzMtcHJvLmlvLyIsImJpcnRoZGF0ZSI6IjE5NTMtMDYtMjAiLCJqdGkiOiI1ODdkZTg1NWQ1NWFiNjhhNTM0MWRjMGMifQ.Gq5tYejChUkMm_ssEdBqVCDB-pT7i1eGHdIV9VaATXA", "type": "link", "sub": "ZH001", "exp": arrow.utcnow().shift(hours=2).timestamp, "aud": "https://idm.c3-pro.io/", "iss": "https://idm.c3-pro.io/" }

doc_linked = { "_id": "587de855d55ab68a5341dc0c", "aud": "https://idm.c3-pro.io/", "sub": "ZH001", "created": 1484646485, "secret": "super-duper-secret", "linked_on": "2017-01-17T10:06:17.394177+00:00", "_jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL2lkbS5jMy1wcm8uaW8vIiwiZXhwIjoxNDg0NzMyODg1LCJzdWIiOiJCcnVubyBNYXJzIiwiYXVkIjoiaHR0cHM6Ly9pZG0uYzMtcHJvLmlvLyIsImJpcnRoZGF0ZSI6IjE5NTMtMDYtMjAiLCJqdGkiOiI1ODdkZTg1NWQ1NWFiNjhhNTM0MWRjMGMifQ.Gq5tYejChUkMm_ssEdBqVCDB-pT7i1eGHdIV9VaATXA", "linked_to": "RANDOM-UUID", "algorithm": "HS256", "exp": arrow.utcnow().shift(hours=2).timestamp, "iss": "https://idm.c3-pro.io/", "changed": 1484647577, "linked_system": "org.c3-pro.app.ios", "type": "link" }
