# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_jwt import JWT, jwt_required

from py import user
from py import jwt_auth
from py import patient
from py.jsondocument import mongoserver

# read settings
try:
	import settings
except Exception:
	logging.warn('No `settings.py` present, using `defaults.py`')
	import defaults as settings


# app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = settings.jwt['secret']
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=int(settings.jwt['expiration_seconds']))
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

def _patient_with_sssid(sssid):
	rslt = patient.Patient.find_sssid_on(sssid, mng_srv, mng_bkt)
	if len(rslt) > 0:
		pat = rslt[0]
		if len(rslt) > 1:
			logging.warn("there are {} patients with SSSID {}".format(len(rslt), sssid))
		return pat
	return None


# routes
@app.route('/')
def index():
	""" The service root.
	"""
	return jsonify({'status': 'ready'})

@app.route('/patients', methods=['GET', 'POST'])
@app.route('/patients/', methods=['GET', 'POST'])
@jwt_required()
def patients():
	if 'POST' == request.method:
		js = request.json
		#return jsonify({'you': 'posted', 'data': js})
		if not js or not 'name' in js or not 'sssid' in js:
			return _err('must at least provide `sssid` and `name`')
		
		# create (unless SSSID already exists)
		pat = _patient_with_sssid(js['sssid'])
		if pat is not None:
			return _err('this SSSID is already taken', 409)
		
		try:
			pat = patient.Patient(js['sssid'], js)
			pat.store_to(mng_srv, mng_bkt)
		except Exception as e:
			return _err(str(e))
		return '', 201
	
	# list
	rslt = patient.Patient.find_on({'type': 'patient'}, mng_srv, mng_bkt)
	return jsonify({'data': [p.for_api() for p in rslt]})

@app.route('/patients/<sssid>', methods=['GET', 'PUT'])
@jwt_required()
def patients_sssid(sssid):
	pat = _patient_with_sssid(sssid)
	if pat is not None:
		
		# update
		if 'PUT' == request.method:
			try:
				pat.safe_update_and_store_to(request.json, mng_srv, mng_bkt)
			except Exception as e:
				return _err(str(e))
			return '', 204
		
		# get
		return jsonify({'data': pat.for_api()})
	return _err('Not Found', 404)


# start the app
if '__main__' == __name__:
	logging.basicConfig(level=logging.DEBUG)
	app.run(debug=True, port=9096)
