FROM nginx:1.27-alpine

# nginx renders /etc/nginx/templates/*.template into /etc/nginx/conf.d/ at start,
# replacing ${BACKEND_URL}. This replaces the default site on port 80.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY . /usr/share/nginx/html/

# Local default: the backend's Compose service name and container port.
# Azure overrides this with the backend Container App's URL.
ENV BACKEND_URL=http://student5-backend:8000

EXPOSE 8000