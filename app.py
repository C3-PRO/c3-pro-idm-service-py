# -*- coding: utf-8 -*-

import json
import logging
from datetime import timedelta
from bson import ObjectId

from flask import Flask, request, jsonify
from flask_jwt import JWT, jwt_required

from py import user
from py import jwt_auth
from py import subject
from py.jsondocument import mongoserver

# read settings
try:
	import settings
except Exception:
	logging.warn('No `settings.py` present, using `defaults.py`')
	import defaults as settings


# JSON encoder that handles BSON
class BSONEncoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, ObjectId):
			return str(o)
		return json.JSONEncoder.default(self, o)


# app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.jwt['secret']
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=int(settings.jwt['expiration_seconds']))
app.json_encoder = BSONEncoder
jwt = JWT(app, jwt_auth.authenticate, jwt_auth.identity)

mng_bkt = settings.mongo_server['bucket']
mng_srv = mongoserver.MongoServer(
	host=settings.mongo_server['host'],
	port=settings.mongo_server['port'],
	database=settings.mongo_server['db'],
	bucket=mng_bkt,
	user=settings.mongo_server['user'],
	pw=settings.mongo_server['password'])

def _err(message, status=400):
	return jsonify({'error': {'status': status, 'message': message}}), status

def _subject_with_sssid(sssid):
	rslt = subject.Subject.find_sssid_on(sssid, mng_srv, mng_bkt)
	if len(rslt) > 0:
		pat = rslt[0]
		if len(rslt) > 1:
			logging.warn("there are {} subjects with SSSID {}".format(len(rslt), sssid))
		return pat
	return None


# routes
@app.route('/')
def index():
	""" The service root.
	"""
	return jsonify({'status': 'ready'})

@app.route('/subject', methods=['GET', 'POST'])
@app.route('/subject/', methods=['GET', 'POST'])
@jwt_required()
def subject():
	
	# create (fails if SSSID already exists)
	if 'POST' == request.method:
		js = request.json
		#return jsonify({'you': 'posted', 'data': js})
		if not js or not 'sssid' in js:
			return _err('must at least provide `sssid`')
		
		subj = _subject_with_sssid(js['sssid'])
		if subj is not None:
			return _err('this SSSID is already taken', 409)
		
		try:
			subject.Subject.validate_json(js)
			subj = subject.Subject(js['sssid'], js)
			del subj._id   # auto-creates UUID; we rely on Mongo
			subj.store_to(mng_srv, mng_bkt)
		except IDMException as e:
			return _err(str(e), status=e.status_code)
		except Exception as e:
			return _err(str(e))
		return jsonify({'data': subj.for_api()}), 201
	
	# list
	rslt = subject.Subject.find_on({'type': 'subject'}, mng_srv, mng_bkt)
	return jsonify({'data': [p.for_api() for p in rslt]})

@app.route('/subject/<sssid>', methods=['GET', 'PUT'])
@jwt_required()
def subject_sssid(sssid):
	subj = _subject_with_sssid(sssid)
	if subj is not None:
		
		# update
		if 'PUT' == request.method:
			try:
				subj.safe_update_and_store_to(request.json, mng_srv, mng_bkt)
			except IDMException as e:
				return _err(str(e), status=e.status_code)
			except Exception as e:
				return _err(str(e))
			return '', 204
		
		# get
		return jsonify({'data': subj.for_api()})
	return _err('Not Found', 404)


# start the app
if '__main__' == __name__:
	logging.basicConfig(level=logging.DEBUG)
	app.run(debug=True, port=9096)
