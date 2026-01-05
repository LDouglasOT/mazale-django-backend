#!/bin/bash

# Deployment script for Django app on Ubuntu VPS
# Run as root or with sudo

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Nginx
sudo apt install nginx -y

# Install Redis (if not using managed)
# sudo apt install redis-server -y

# Install Certbot for SSL
sudo apt install snapd -y
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Create app directory (if not cloned)
# cd /var/www
# sudo mkdir mazale
# sudo chown ubuntu:ubuntu mazale
# git clone <repo> mazale


# Create virtual environment as ubuntu user
sudo -u ubuntu python3 -m venv venv

# Upgrade pip and install dependencies as ubuntu user
sudo -u ubuntu bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && pip install gunicorn"

# Create .env file
sudo -u ubuntu cp .env.example .env
# Edit .env with actual values

# Run migrations as ubuntu user
sudo -u ubuntu bash -c "source venv/bin/activate && python manage.py migrate"

# Collect static files as ubuntu user
sudo -u ubuntu bash -c "source venv/bin/activate && python manage.py collectstatic --noinput"

# Create systemd service for Gunicorn
sudo tee /etc/systemd/system/mazale.service > /dev/null <<EOF
[Unit]
Description=Mazale Django App
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/mazale-django-backend
Environment="PATH=/home/ubuntu/mazale-django-backend/venv/bin"
ExecStart=/home/ubuntu/mazale-django-backend/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/mazale-django-backend/mazale.sock mazale.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start mazale
sudo systemctl enable mazale

# Configure Nginx
sudo tee /etc/nginx/sites-available/mazale > /dev/null <<EOF
server {
    listen 80;
    server_name sugarmummiesug.online www.sugarmummiesug.online 13.53.125.194;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias /home/ubuntu/mazale-django-backend/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/mazale-django-backend/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/mazale-django-backend/mazale.sock;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/mazale /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl reload nginx

# Get SSL certificate
sudo certbot --nginx -d sugarmummiesug.online -d www.sugarmummiesug.online

# Set up Celery (if needed)
# Create celery.service and celerybeat.service similar to gunicorn

echo "Deployment complete. Check logs with: sudo journalctl -u mazale"