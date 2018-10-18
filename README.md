# 301hub, a single place to handle all of your http (and https) redirects, yay!

In a world where everything runs on SSL, something as simple as setting up a redirect requires setting up an entire server.  This project aims to encapsulate all of the gruntwork into an easy to deploy package.

# Use cases

- your website is hosted on a dynamic ip, requiring you to have a dns CNAME but preventing you from being able to use an A record for the nexus.  AWS ELB/ALB applications fall into this category.
- your website will be down and you want to redirect temporarily
- you just think setting up redirects is a thing

# Conf

Check out conf.example.json which contains two example redirects

```
{
"email" : "you@example.com",
"redirects": 
    [
        {
            "from": "your.awesome.site.com",
            "to" : "some_other.com"
        },{
            "from": "example.com",
            "to" : "www.example.com"
        }
    ]
}
```

- your.awesome.site.com gets 301'd to some_other.com
- example.com gets 301'd to www.example.com

# Installation

<code>docker pull jbeeson/301hub</code>

or clone this repo and check out the docker-compose.yml file

# Getting started

* You'll need a server with a fixed ip, docker and docker-compose with ports 80 and 443 exposed to the internets
* Create one or more dns A records or CNAMEs pointing to your server
* clone this repository
* make a conf.json that has the same formatting as the above example.
* For each dns record, create a redirect
* Make a docker volume called 301hub_sslcerts `docker volume create 301hub_sslcerts` this will contain the ssl certs (duh)
* `docker-compose build; docker-compose up -d` and voilà

# Additional stuff to know
* 301hub uses let's encrypt for its SSL certs.  It auto requests them and auto renews them (they expire every 90 days) out of the box.
* Non valid entries in conf.json will not cause failure, nginx will still come up, but the redirect will not work.  You'll want to check the docker logs `docker-compose logs nginx`
* When you run setup it will check that the "from" domain actually resolves to its self.  It also checks that the "to" field does NOT resolve to its self to avoid inifinite loops
* Visitors who go to your ip using the ip or a hostname for which there is no redirect will get a big a fat HTTP 500 in their face.
* nginx is rate limited to 5 requests per second per ip
* the included nginx configuration is meant to be pretty secure and low memory, you can run this on a small cheapo server and not need to worry about firewall stuff.
* You can manually run setup at any time in a running container to take configuration changes into account and renew any eligible certificates

# Environment variables


- `SETUP_REFRESH_FREQUENCY` in seconds, how often the setup program will run, default is once every 24 hours
- `CERT_EXPIRE_CUTOFF_DAYS` how many days before the 90 days epiration should the certificats be renewed.  7 by default is good enough for an always-on server
- `CHECK_IP_URL` 301 uses this external service to know its public ip, default is http://ip.42.pl/raw
- `MY_HOSTNAME` set this to your server's hostname

<img src='301.png'>
