FROM nginx:alpine

COPY templates/ /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
# nginx:alpine renders /etc/nginx/templates/*.template through envsubst at start-up
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

# Default for local docker-compose; deploy-azure.sh overrides it in Azure
ENV BACKEND_SERVICE_URL=http://student2-backend:5001

EXPOSE 80
