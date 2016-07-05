C3-PRO IDM Service (Python)
===========================

This is a Python-Flask and MongoDB-based backend service for the IDM frontend services.
The server maintains its own user database and uses [JWT](http://jwt.io) (via [Flask-JWT](https://pythonhosted.org/Flask-JWT/)) for authorization.


API
---

### /patient




Authorization
-------------

To get a token, make a request to the `/auth` resource:

```
POST /auth HTTP/1.1
Host: localhost:8080
Content-Type: application/json

{
  "username": "john@doe.com",
  "password": "pass"
}
```


Installation
------------


Starting the Server
-------------------

Before launching you may want to configure the server.
All default settings reside in `defaults.py` and this file is used if there is no `settings.py`.
It's best if you create `settings.py` at the root directory yourself, `import defaults` at the top and then override whatever setting you want to customize.
By default the server runs on port `9096`.

In production it's best to let _gunicorn_ take care of launching the web app:

```bash
```

During development you can use:

```bash
$ python app.py
```
