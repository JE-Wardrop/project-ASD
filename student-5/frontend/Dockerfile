FROM nginx:1.27-alpine

# nginx renders /etc/nginx/templates/*.template into /etc/nginx/conf.d/ when the
# container starts, replacing ${BACKEND_URL}. Remove the default site (port 80) first.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY . /usr/share/nginx/html/

# Local default: the backend's Compose service name and container port.
# Azure overrides it with the backend Container App's URL.
ENV BACKEND_URL=http://student5-backend:8000

EXPOSE 8000