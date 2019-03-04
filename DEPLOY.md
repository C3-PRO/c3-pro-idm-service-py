Python IDM Service Deployment
=============================

This setup will run both backend and frontend on one VM.
We'll assume a dualcore Ubuntu Linux 16.04 64 bit “Xenial” machine.

SSH into your machine and clone this repo somewhere.
We'll refer to this repo's location with `PATH_TO_REPO` below.

All the config files have a sample domain name hardcoded (“idm.domain.io”) and some commands below will also assume this domain.
You will want to change those occurrences.


## HTTPS

We set up letsencrypt before starting nginx using a standalone cert server.
[See here](https://certbot.eff.org/#ubuntuxenial-nginx) for documentation.

    apt-get apt-get update
    apt-get install software-properties-common
    add-apt-repository universe
    add-apt-repository ppa:certbot/certbot
    apt-get update
    apt-get install certbot python-certbot-nginx
    
    certbot certonly --nginx -d idm.domain.io

These certs expire after 90 days, setup _systemd_ to auto-renew:

    cp {PATH_TO_REPO}/systemd/* /etc/systemd/system/
    systemctl start letsencrypt.renew.timer
    systemctl enable letsencrypt.renew.timer


## Nginx

Requests will be reverse proxied through Nginx.

    apt install nginx
    cp {PATH_TO_REPO}/nginx-site.c3-pro-idm /etc/nginx/sites-enabled/c3-pro-idm
    service nginx start


## MongoDB

    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
    echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.2.list
    apt-get update
    apt-get install -y mongodb-org

Configure Mongo with systemd:

    # if not already done in the HTTPS step:
    # cp {PATH_TO_REPO}/systemd/mongodb.service /etc/systemd/system/.
    systemctl enable mongodb.service
    systemctl start mongodb
    systemctl status mongodb


## App, WSGI, Hypervisor

Our Flask app is a WSGI app for which we'll set up a virtual environment, which will be run by gunicorn which in turn will be kept running by supervisor.

    apt-get install -y supervisor
    cp {PATH_TO_REPO}/supervisor.c3-pro-idm.conf /etc/supervisor/conf.d/c3-pro-idm.conf
    # workaround for Ubuntu 16.04 (next 2 lines)
    systemctl enable supervisor.service
    systemctl start supervisor
    supervisorctl reload

After we set up the virtual environment for the IDM, we no longer need to be root:

    apt install -y python-pip
    pip install virtualenv
    # exit root and re-connect using the desired user
    cd {PATH_TO_REPO}
    virtualenv -p python3 env
    . env/bin/activate
    pip install -r requirements.txt
    deactivate

Now your machine should respond when contacted on port 80 or 443.
