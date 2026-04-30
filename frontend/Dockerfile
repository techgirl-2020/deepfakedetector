FROM nginx:alpine

COPY default.conf /etc/nginx/conf.d/default.conf
COPY index.html login.html dashboard.html /usr/share/nginx/html/
COPY css /usr/share/nginx/html/css
COPY js /usr/share/nginx/html/js

EXPOSE 80
