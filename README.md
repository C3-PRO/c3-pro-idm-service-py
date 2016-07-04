C3-PRO IDM Service (Python)
===========================

This is a Python-Flask and MongoDB-based backend service for the IDM frontend services.
The server maintains its own user database and uses [JWT](http://jwt.io) (via [Flask-JWT](https://pythonhosted.org/Flask-JWT/)) for authorization.


API
---


Authorization
-------------

To get a token, make a request to the `/auth` resource:

POST /auth HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "username": "john@doe.com",
  "password": "pass"
}


Installation
------------

