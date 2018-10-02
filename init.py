#!/usr/bin/env python

import json, os
from subprocess import Popen, PIPE
from OpenSSL import crypto
import datetime
import shutil

CERT_PATH = '/etc/letsencrypt/live'
CONF_PATH = '/etc/nginx/conf.d/'
CERT_EXPIRE_CUTOFF_DAYS = 7

def template(**kwargs):
    template = """
    server {
        listen {http_port} ;
        server_name {server_name};

        if ($host !~ ^({server_name})$ ) {
            return 500;
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

        ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
        ssl_certificate {CERT_PATH}/{server_name}/fullchain.pem;
        ssl_certificate_key {CERT_PATH}/{server_name}/privkey.pem;
        
        if ($host !~ ^({server_name})$ ) {
            return 500;
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

def main():
    with open('conf.json', 'r') as f:
        conf = json.load(f)
    
    for d in conf["redirects"]:
        cert_file=CERT_PATH+'/'+d['from']+'/cert.pem'
        if os.path.isfile(cert_file):
            # cert already exists
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, open(cert_file).read())
            exp = datetime.datetime.strptime(cert.get_notAfter(), '%Y%m%d%H%M%SZ')
            
            expires_in = exp - datetime.datetime.utcnow()
            
            if expires_in.days > 0:
                log("Found cert {}, expires in {} days".format(d['from'], expires_in.days))
            else:
                log("Found cert {} EXPIRED".format(d['from']))
                
            if expires_in.days < CERT_EXPIRE_CUTOFF_DAYS:
                log("Deleting cert {} to force renewal".format(d['from']))
                # time to renew
                try:
                    shutil.rmtree(CERT_PATH+'/'+d['from'])
                except:
                    pass
            

        try:
            email = d['email']
        except:
            email = conf['email']
            
        cmd = '/usr/bin/certbot certonly --verbose --noninteractive --quiet --standalone --agree-tos --email="{}" '.format(email)
        cmd += ' -d "{}"'.format(d['from'])

        from2 = d['from'].replace('/', '_')
        nginx_conf = template(http_port=80, https_port=443, server_name=d['from'], forward_to=d['to'])
        
        conf_file = '{}/{}'.format(CONF_PATH, from2)
        if os.path.isfile(conf_file):
            os.remove(conf_file)
            
        #log(nginx_conf)
        #log(cmd)
    
        if not os.path.isfile(cert_file):
            (out, err, exitcode) = run(cmd)
            
            if exitcode != 0:
                log("Requesting cert for {}: FAILED".format(d['to']))
                log(cmd)
                log(err)
            else:
                log("Requesting cert for {}: SUCCESS".format(d['to']))
                # write conf
                with open(conf_file, 'w') as f:
                    f.write(nginx_conf)
        else:
            # write conf
            with open(conf_file, 'w') as f:
                f.write(nginx_conf)
            
main()