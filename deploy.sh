#!/bin/bash

# Deployment script for Mazale Django app on Ubuntu VPS
# Run as root or with sudo

APP_DIR="/home/ubuntu/mazale-django-backend"

# 1. Update system and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx snapd -y

# 2. Setup Certbot for SSL
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
[ -f /usr/bin/certbot ] || sudo ln -s /snap/bin/certbot /usr/bin/certbot

# 3. FIX PERMISSIONS (Crucial: Allows Nginx to access the socket)
sudo chmod 755 /home/ubuntu
sudo chown -R ubuntu:www-data $APP_DIR

# 4. Create virtual environment and logs directory as ubuntu user
sudo -u ubuntu python3 -m venv $APP_DIR/venv
sudo -u ubuntu mkdir -p $APP_DIR/logs

# 5. Install dependencies
# Using numpy>=1.26.0 for Python 3.12+ support
sudo -u ubuntu bash -c "source $APP_DIR/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install 'numpy>=1.26.0' Pillow gunicorn python-decouple && \
    pip install -r $APP_DIR/requirements.txt"

# 6. Django Tasks
sudo -u ubuntu bash -c "source $APP_DIR/venv/bin/activate && python $APP_DIR/manage.py migrate --noinput"
sudo -u ubuntu bash -c "source $APP_DIR/venv/bin/activate && python $APP_DIR/manage.py collectstatic --noinput"

# 7. Create systemd service for Gunicorn
sudo tee /etc/systemd/system/mazale.service > /dev/null <<EOF
[Unit]
Description=Mazale Django App
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
# Removes stale socket before starting
ExecStartPre=/usr/bin/rm -f $APP_DIR/mazale.sock
ExecStart=$APP_DIR/venv/bin/gunicorn \\
    --access-logfile $APP_DIR/logs/access.log \\
    --error-logfile $APP_DIR/logs/error.log \\
    --log-level info \\
    --workers 3 \\
    --bind unix:$APP_DIR/mazale.sock \\
    mazale.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

# 8. Configure Nginx
sudo tee /etc/nginx/sites-available/mazale > /dev/null <<EOF
server {
    listen 80;
    server_name sugarmummiesug.online www.sugarmummiesug.online 13.53.125.194;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias $APP_DIR/staticfiles/;
    }

    location /media/ {
        alias $APP_DIR/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/mazale.sock;
    }
}
EOF

# 9. Enable and Restart Services
sudo ln -sf /etc/nginx/sites-available/mazale /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable mazale
sudo systemctl restart mazale
sudo systemctl restart nginx

# 10. SSL (Uncomment after verifying the site works on HTTP)
# sudo certbot --nginx -d sugarmummiesug.online -d www.sugarmummiesug.online --non-interactive --agree-tos -m admin@sugarmummiesug.online

echo "Deployment complete. Check logs at $APP_DIR/logs/error.log"
