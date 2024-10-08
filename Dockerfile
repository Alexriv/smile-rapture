# Use an official NGINX image as the base image
FROM nginx:alpine

# Set the working directory inside the container
WORKDIR /usr/share/nginx/html

# Copy the website files from the current directory to the NGINX web root
COPY . .

# Expose port 80 to allow external access
EXPOSE 80

# Start NGINX in the foreground to keep the container running
CMD ["nginx", "-g", "daemon off;"]
