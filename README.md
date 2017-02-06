C3-PRO IDM Service (Python)
===========================

This is a Python-Flask and MongoDB-based backend service for the **C3-PRO IDM frontend services**, adhering to the [IDM API spec](http://docs.c3proidm.apiary.io).
The server maintains its own user database and uses [JWT](http://jwt.io) (via [Flask-JWT](https://pythonhosted.org/Flask-JWT/)) for authorization.


User Management
---------------

In addition to the API endpoints defined by the [IDM API spec](http://docs.c3proidm.apiary.io), this service provides endpoints for user management.

### Admin Setup

After installation, the `/init` endpoint will allow to create an admin users.
It can be accessed without password as long as no admin user is present on the system.

### Create Users

The `/user` endpoint will accept `POST` requests with the following payload, if a JWT bearer token _belonging to an admin_ is provided.
**Note** that usernames are supposed to be email addresses and will be used to reset passwords.

```
POST /user HTTP/1.1
Content-Type: application/json
Authorization: JWT eyJ0eXA...

{
    "username": "{user's email}",
    "password": "{password}",
    "admin": true/false
}
```

At this time there is no possibility to change usernames; create a new user instead.
A `DELETE` request to the `/user` endpoint with a JSON containing `username` will delete this user, if signed with an admin JWT.

You can use the simple Python 3 script `create_users.py` contained in this repository to add users via the command line.

### Password Reset

The user can navigate to the `/iforgot` endpoint, which will allow to reset one's password.
This will trigger an email sent to the user's _username_, which contains a link to `/reset` with a one-time token.
The reset screen allows to set a new password.


Authorization
-------------

To get a token, make a request to the `/auth` resource:

```
POST /auth HTTP/1.1
Content-Type: application/json

{
  "username": "john@doe.com",
  "password": "pass"
}
```


Installation
------------

Our Flask app is a _WSGI_ app for which we'll set up a _virtual environment_, which will be run by _gunicorn_ which in turn will be kept running by _supervisor_.

Requests will be reverse proxied through _Nginx_.

### See [DEPLOY.md](./DEPLOY.md).


Starting the Server
-------------------

Before launching you may want to configure the server.
All default settings reside in `defaults.py` and this file is used if there is no `settings.py`.
It's best if you create `settings.py` at the root directory yourself, `import defaults` at the top and then override whatever setting you want to customize.
By default the server runs on port `9096`.

In production it's best to let _gunicorn_ take care of launching the web app.
The following will run the app on 5 worker threads (appropriate for a dual-core machine) on port `9096`:

```bash
gunicorn -w 5 app:app -b 0.0.0.0:9096
```

During development you can use:

```bash
python app.py
```
