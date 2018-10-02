FROM nginx:mainline-alpine

EXPOSE 80 443

RUN apk add --no-cache bash certbot python

RUN mkdir -p /sslcert

RUN rm /etc/nginx/conf.d/* 
RUN rm /etc/nginx/nginx.conf

ADD nginx.conf /etc/nginx/

ADD init.py /
ADD run.sh /
RUN chmod +x /init.py /run.sh

ADD conf.json /

CMD ["/run.sh"]