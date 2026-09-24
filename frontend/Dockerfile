# Noteboard frontend image
# Base: nginx:alpine — serves static HTML and proxies /api/ to backend
FROM nginx:alpine

# Remove default nginx config and replace with ours
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/noteboard.conf

# Copy static frontend files
COPY src/ /usr/share/nginx/html/

EXPOSE 80
