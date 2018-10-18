FROM nginx:mainline-alpine

EXPOSE 80 443

RUN apk add --no-cache bash certbot python

RUN mkdir -p /sslcert

RUN rm /etc/nginx/conf.d/* 
RUN rm /etc/nginx/nginx.conf

ADD nginx.conf /etc/nginx/

RUN mkdir -p /etc/301hub

ADD setup.py /usr/local/bin/setup
ADD run.sh /
RUN chmod +x /usr/local/bin/setup /run.sh

ADD conf.example.json /etc/301hub/

CMD ["/run.sh"]