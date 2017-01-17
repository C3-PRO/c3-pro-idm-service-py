# -*- coding: utf-8 -*-

import json
import logging
from datetime import timedelta
from bson import ObjectId

from flask import Flask, request, redirect, jsonify, render_template
from flask_jwt import JWT, jwt_required, current_identity

from py import user
from py import jwt_auth
from py import subject
from py import link
from py.idmexception import IDMException
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

user.server = mng_srv
user.bucket = mng_bkt

def _err(message, status=400, headers=None):
	body = jsonify({'error': {'status': status, 'message': message}})
	return (body, status, headers) if headers is not None else (body, status)

def _exc(exception):
	if isinstance(exception, IDMException):
		return _err(str(exception), status=exception.status_code)
	return _err(str(exception))

@app.errorhandler(404)
def _not_found(error):
	return _err(error.name, status=error.code)

@app.errorhandler(405)
def _not_allowed(error):
	return _err(error.name, status=error.code, headers={'Allow': ', '.join(error.valid_methods)})

@jwt.jwt_error_handler
def _jwt_err(error):
	return _err(error.error, status=error.status_code, headers=error.headers)

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


# MARK: - Subjects

@app.route('/subject', methods=['GET', 'POST'])
@jwt_required()
def subject_ep():
	try:
		# create (fails if SSSID already exists)
		if 'POST' == request.method:
			js = request.json
			#return jsonify({'you': 'posted', 'data': js})
			if not js or not 'sssid' in js:
				return _err('must at least provide `sssid`')
			
			subj = _subject_with_sssid(js['sssid'])
			if subj is not None:
				return _err('this SSSID is already taken', 409)
			
			subj = subject.Subject(js['sssid'], js)
			del subj._id   # auto-creates UUID; we rely on Mongo
			subj.store_to(mng_srv, mng_bkt)
			return jsonify({'data': subj.for_api()}), 201
		
		# list subjects
		search = request.args.get('search')
		page = request.args.get('page')
		limit = request.args.get('perpage')
		skip = int(page) * int(limit) if page and limit else None
		sort = request.args.get('ordercol')
		order = request.args.get('orderdir')
		desc = True if order and 'desc' == order.lower() else False
		rslt = subject.Subject.find_on({'type': 'subject'}, mng_srv, mng_bkt, skip, int(limit), sort, desc)
		return jsonify({'data': [p.for_api() for p in rslt]})
	except Exception as e:
		return _exc(e)

@app.route('/subject/<sssid>', methods=['GET', 'PUT'])
@jwt_required()
def subject_sssid(sssid):
	try:
		subj = _subject_with_sssid(sssid)
		if subj is None:
			return _err('Not Found', status=404)
		
		# update subject
		if 'PUT' == request.method:
			subj.safe_update_and_store_to(request.json, mng_srv, mng_bkt)
			return '', 204
		
		# get subject
		return jsonify({'data': subj.for_api()})
	except Exception as e:
		return _exc(e)


# MARK: - Links

@app.route('/link/<jti>/jwt', methods=['GET'])
def link_jti_jwt(jti):
	try:
		lnk = link.Link.find_jti_on(jti, mng_srv, mng_bkt)
		if lnk is None:
			return _err('Not Found', status=404)
		return lnk.jwt(mng_srv, bucket=mng_bkt)
	except Exception as e:
		return _exc(e)

@app.route('/establish', methods=['POST'])
def establish_ep():
	try:
		auth = request.headers.get('Authorization')
		if not auth:
			raise IDMException('Unauthorized', 401)
		auth_list = auth.split(' ')
		if 2 != len(auth_list) or ('Bearer' != auth_list[0] and 'JWT' != auth_list[0]):
			raise IDMException('only `Bearer` and `JWT` type authorization is acceptable', 406)
		
		link.Link.link_jwt_to_fhir_patient(auth_list[1], request.json, mng_srv, mng_bkt)
		return '', 204
	
	except Exception as e:
		return _exc(e)

@app.route('/link/<jti>', methods=['GET', 'PUT'])
@jwt_required()
def link_jti(jti):
	try:
		lnk = link.Link.find_jti_on(jti, mng_srv, mng_bkt)
		if lnk is None:
			return _err('Not Found', status=404)
		
		# update link
		if 'PUT' == request.method:
			lnk.safe_update_and_store_to(request.json, mng_srv, mng_bkt)
			return 'Not implemented', 500
		
		# get
		return jsonify({'data': lnk.for_api()})
	except Exception as e:
		return _exc(e)

@app.route('/subject/<sssid>/links', methods=['GET', 'POST'])
@jwt_required()
def subject_sssid_link(sssid):
	try:
		subj = _subject_with_sssid(sssid)
		if subj is None:
			return _err('Not Found', status=404)

		# create a new link
		if 'POST' == request.method:
			lnk = subj.create_new_link(settings, mng_srv, mng_bkt)
			return jsonify({'data': lnk.for_api()}), 201
		
		# return all links for this SSSID
		rslt = link.Link.find_on({'type': 'link', 'sssid': sssid}, mng_srv, mng_bkt)
		return jsonify({'data': [l.for_api() for l in rslt]})
	except Exception as e:
		return _exc(e)


# MARK: - Users

@app.route('/iforgot', methods=['GET', 'POST'])
def iforgot_ep():
	msg = "If you have forgotten your password, provide your username below and we will send you an email with a link that allows you to set a new password."
	errmsg = None
	if 'POST' == request.method:
		try:
			name = request.form.get('username')
			if not name:
				raise IDMException("you must provide a username")
			usr = user.User.get(name, mng_srv, bucket=mng_bkt)
			hsh = usr.temporary_pass_hash(mng_srv, bucket=mng_bkt)
			lnk = "{}/reset?k={}".format(request.url_root, hsh).replace('//', '/')
			usr.email_temporary_pass(sender=settings.admin_email, link=lnk)
			msg = "A password reset link has been sent to your email address. Follow the link in the email to set a new password."
		except Exception as e:
			errmsg = str(e)
	return render_template('iforgot.html', message=msg, errormessage=errmsg)

@app.route('/reset', methods=['GET', 'POST'])
def reset_ep():
	msg = None
	errmsg = None
	try:
		if 'POST' == request.method:
			key = request.form.get('key')
			pass1 = request.form.get('pass1')
			pass2 = request.form.get('pass2')
			user.User.reset_password_for(key, pass1, pass2, mng_srv, bucket=mng_bkt)
			msg = "your password has been set"
		else:
			key = request.args.get('k')
			if not key:
				raise IDMException("your password reset link seems to be broken, no reset key was detected. Please check your email and try again.")
	except Exception as e:
		errmsg = str(e)
	return render_template('reset.html', key=key, message=msg, errormessage=errmsg)

@app.route('/init', methods=['GET', 'POST'])
def init_ep():
	has_admins = user.User.has_admins(mng_srv, mng_bkt)
	if not has_admins:
		if 'POST' == request.method:
			try:
				name = request.form.get('username')
				pw = request.form.get('password')
				user.User.create(name, pw, request.form.get('admin'), mng_srv, mng_bkt)
				has_admins = user.User.has_admins(mng_srv, mng_bkt)
			except Exception as e:
				return render_template('create.html', username=name, errormessage=str(e))
		
		if not has_admins:
			return render_template('create.html', message="No admin users are present on the system, you can create one now:")
	return render_template('done.html')

@app.route('/user', methods=['POST'])
@jwt_required()
def user_ep():
	try:
		if not current_identity.admin:
			raise IDMException("you do not have privileges to create a new user", 403)
		name = request.json.get('username')
		pw = request.json.get('password')
		usr = user.User.create(name, pw, request.json.get('admin'), mng_srv, mng_bkt)
		return jsonify({'data': usr.for_api()})
	except Exception as e:
		return _exc(e)

@app.route('/user/<uid>', methods=['GET', 'PUT'])
@jwt_required()
def user_uid(uid):
	try:
		# TODO: implement PUT
		usr = user.User.get(uid, mng_srv, mng_bkt)
		return jsonify({'data': usr.for_api()})
	except Exception as e:
		return _exc(e)


# start the app
if '__main__' == __name__:
	logging.basicConfig(level=logging.INFO)
	app.run(debug=True, port=9096)

