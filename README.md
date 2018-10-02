# 301 hub, a server that does a bunch of 301 stuff, yay!


docker run \
  -v le_sslcert:/etc/letsencrypt \
  -e http_proxy=$http_proxy \
  -e domains="$LE_DOMAIN" \
  -e email="$LE_EMAIL" \
  -p 80:80 \
  -p 443:443 \
  --rm pierreprinetti/certbot:latest
  
  
  
https://certbot.eff.org/docs/using.html