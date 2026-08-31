
FROM nginx:1.27-alpine

COPY . /usr/share/nginx/html/

# This container will run on port 8000 instead of the default port 80
RUN sed -i 's/listen       80;/listen       8000;/' /etc/nginx/conf.d/default.conf

EXPOSE 8000