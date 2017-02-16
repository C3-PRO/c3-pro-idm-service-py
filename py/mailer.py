# -*- coding: utf-8 -*-

import smtplib
from email.mime.text import MIMEText


class Mailer(object):
	""" Simple implementation of a mailing facility using smtplib.
	"""
	
	def __init__(self, username, password, server, port, reply_to=None):
		self.s = None
		self.server = server
		self.port = port
		self.username = username
		self.password = password
		self.reply_to = reply_to if reply_to is not None else username
	
	def connect(self):
		s = smtplib.SMTP(self.server, self.port)
		s.ehlo()
		s.starttls()
		s.ehlo()
		s.login(self.username, self.password)
		self.s = s
	
	def send_mail(self, to, subject, body):
		self.connect()
		msg = MIMEText(body)
		msg['Subject'] = subject
		msg['From'] = self.username
		msg['Reply-To'] = self.reply_to
		msg['To'] = to
		
		self.s.sendmail(self.username, to, msg.as_string())
		self.s.close()

