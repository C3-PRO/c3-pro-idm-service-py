# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from flask import Flask, request, jsonify
from flask_jwt import JWT, jwt_required, current_identity

from py import user
from py import jwt_auth


# app setup (TODO: move to configuration)
app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-duper-secret'
app.config['JWT_EXPIRATION_DELTA'] = timedelta(seconds=3600)
jwt = JWT(app, jwt_auth.authenticate, jwt_auth.identity)


# routes
@app.route('/')
def index():
	""" The service root.
	"""
	return jsonify({'status': 'ready'})

@app.route('/patients')
@app.route('/patients/')
@jwt_required()
def patients():
	return '{}'.format(current_identity)

@app.route('/patients/<pid>')
@jwt_required()
def patients_pid(pid):
	pass


# start the app
if '__main__' == __name__:
	logging.basicConfig(level=logging.DEBUG)
	app.run(debug=True, port=8080)
