#!/usr/bin/env python

import json, os
from subprocess import Popen, PIPE
from OpenSSL import crypto
import datetime
import shutil
from urlparse import urlparse
from urllib2 import urlopen
import socket

CERTBOT_PORT=os.environ.get('CERTBOT_PORT', '8086')
CONF_PATH = os.environ.get('CONF_PATH', '/etc/301hub/conf.json')
CERT_PATH = os.environ.get('CERT_PATH', '/etc/letsencrypt/live')
NGINX_CONF_PATH = os.environ.get('NGINX_CONF_PATH', '/etc/nginx/conf.d/')
CERT_EXPIRE_CUTOFF_DAYS = int(os.environ.get('CERT_EXPIRE_CUTOFF_DAYS', 7))

MY_IP=''

def template(**kwargs):
    template = """
    server {
        listen {http_port} ;
        server_name {server_name};

        limit_req zone=mylimit;

        location /.well-known/acme-challenge {
            proxy_pass http://127.0.0.1:{CERTBOT_PORT};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        if ($host !~ ^({server_name})$ ) {
            return 404;
        }
            
        if ($request_method !~ ^(GET|HEAD|POST)$ )
        {
            return 405;
        }
        return 301 http://{forward_to}$request_uri;

    }
    server {
        listen {https_port} ssl http2;
        server_name {server_name};
    
        limit_req zone=mylimit;

        ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
        ssl_certificate {CERT_PATH}/{server_name}/fullchain.pem;
        ssl_certificate_key {CERT_PATH}/{server_name}/privkey.pem;
        
        location /.well-known/acme-challenge {
            proxy_pass http://127.0.0.1:{CERTBOT_PORT};
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        if ($host !~ ^({server_name})$ ) {
            return 404;
        }
            
        if ($request_method !~ ^(GET|HEAD|POST)$ )
        {
            return 405;
        }
        return 301 https://{forward_to}$request_uri;

    }
    """

    out = template

    out = out.replace(u'{CERT_PATH}', u'{}'.format(CERT_PATH))
    out = out.replace(u'{CERTBOT_PORT}', u'{}'.format(CERTBOT_PORT))
    
    if kwargs is not None:
        for k, v in kwargs.iteritems():
            out = out.replace(u'{'+k+'}', u'{}'.format(v))
    return out
    

def run(cmd, splitlines=False):
    # you had better escape cmd cause it's goin to the shell as is
    proc = Popen([cmd], stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    out, err = proc.communicate()
    if splitlines:
        out_split = []
        for line in out.split("\n"):
            line = line.strip()
            if line != '':
                out_split.append(line)
        out = out_split

    exitcode = int(proc.returncode)

    return (out, err, exitcode)


def log(s):
    print(s)


def get_my_ip():
    global MY_IP
    if MY_IP == '':
        MY_IP = urlopen('http://ip.42.pl/raw').read()
        log("My ip appears to be {}".format(MY_IP))

def points_to_me(s):
    get_my_ip()
    
    url = 'http://{}'.format(s)
    # from urlparse import urlparse  # Python 2
    parsed_uri = urlparse(url)
    domain = parsed_uri.netloc.split(':')[0]
    success = False
    ip = None
    try:
        ip = socket.gethostbyname(domain)

        if ip == MY_IP:
            success = True
    except Exception as e:
        log(e)
        
    return (success, domain, ip, MY_IP)

def main():
    try:
        with open(CONF_PATH, 'r') as f:
            conf = json.load(f)
    except IOError:
        log("ERROR: No config file found at {}".format(CONF_PATH))
        log("QUITTING")
        exit(-1)
    
    nginx_reload = False
    
    for d in conf["redirects"]:
        
        cert_file=CERT_PATH+'/'+d['from']+'/cert.pem'
        (points_to_me_from, domain, ip, my_ip) = points_to_me(d['from'])
        (points_to_me_to, domain, ip, my_ip) = points_to_me(d['to'])

        if ip == None:
            log("DNS ERROR: No DNS entry found for {}.  Update DNS records and rerun setup".format(domain))
            continue
        
        if not points_to_me_from:
            log("DNS ERROR: Cannot request or renew certificate for {}.  It points to {} rather than my ip, which is {}.  Update DNS records and rerun setup".format(domain, ip, my_ip))
            if os.path.isfile(cert_file):
                os.remove(conf_file)
                nginx_reload = True
            continue

        if points_to_me_to:
            log("CONFIG ERROR: Cannot forward {} to {}.  {} routes to my ip, {} which would make an infinite loop".format(domain, ip, domain, my_ip))
            if os.path.isfile(cert_file):
                os.remove(conf_file)
                nginx_reload = True
            continue
        
        if os.path.isfile(cert_file):
            # cert already exists
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_file).read())
            exp = datetime.datetime.strptime(cert.get_notAfter(), '%Y%m%d%H%M%SZ')
            
            expires_in = exp - datetime.datetime.utcnow()
            
            if expires_in.days <= 0:
                log("Found cert {} EXPIRED".format(d['from']))
            else:
                log("Found cert {}, expires in {} days".format(d['from'], expires_in.days))
    
            if expires_in.days < CERT_EXPIRE_CUTOFF_DAYS:
                log("Trying to renew cert {}".format(d['from']))
                cmd = "certbot renew --verbose --noninteractive --standalone  --http-01-port 8086 --agree-tos -d {}".format(d['from'])
                (out, err, exitcode) = run(cmd)
                
                if exitcode == 0:
                    log("RENEW SUCCESS: Certificate {} successfully renewed".format(domain))
                    nginx_reload = True

                else:
                    log("RENEW FAIL: ERROR renewing certificate {}".format(domain))
                    log(out)
                    log(err)
                    
        try:
            email = d['email']
        except KeyError:
            email = conf['email']
            
        cmd = 'certbot certonly --verbose --noninteractive --quiet --standalone  --http-01-port {} --agree-tos --email="{}" '.format(CERTBOT_PORT, email)
        cmd += ' -d "{}"'.format(d['from'])

        from2 = d['from'].replace('/', '_')
        nginx_conf = template(http_port=80, https_port=443, server_name=d['from'], forward_to=d['to'])
        
        conf_file = '{}/{}'.format(NGINX_CONF_PATH, from2)
        if os.path.isfile(conf_file):
            os.remove(conf_file)
        
        if not os.path.isfile(cert_file):
            lookup(d['from'])
            
            (out, err, exitcode) = run(cmd)
            
            if exitcode != 0:
                log("Requesting cert for {}: FAILED".format(d['from']))
                log(cmd)
                log(err)
            else:
                log("Requesting cert for {}: SUCCESS".format(d['from']))
                # write conf
                with open(conf_file, 'w') as f:
                    f.write(nginx_conf)
                nginx_reload = True
        else:
            # write conf
            with open(conf_file, 'w') as f:
                f.write(nginx_conf)
    
    if nginx_reload:
        run("nginx -s reload")
            
main()