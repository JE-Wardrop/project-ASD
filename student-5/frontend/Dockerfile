# Student 5 - Transaction Management
# FRONTEND MICROSERVICE - chi la file tinh, dung nginx

FROM nginx:1.27-alpine

COPY . /usr/share/nginx/html/

# Quy uoc nhom: moi container lang nghe cong 8000 ben trong network
RUN sed -i 's/listen       80;/listen       8000;/' /etc/nginx/conf.d/default.conf

EXPOSE 8000
