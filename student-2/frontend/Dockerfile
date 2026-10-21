FROM nginx:alpine

# nginx renders /etc/nginx/templates/*.template into /etc/nginx/conf.d/ at start,
# replacing ${BACKEND_URL}. This replaces the default site.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/

# Local default: the backend's Compose service name and container port.
# Azure overrides this with the backend Container App's URL.
ENV BACKEND_URL=http://student2-backend:5001

EXPOSE 80
