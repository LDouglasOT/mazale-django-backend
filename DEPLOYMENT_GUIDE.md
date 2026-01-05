# Django Backend Deployment Guide

This guide provides step-by-step instructions for deploying the Mazale Django backend to a VPS with IP 13.53.125.194 and domain sugarmummiesug.online.

## Prerequisites

- Ubuntu VPS (recommended 20.04 or later)
- Domain name (sugarmummiesug.online) pointed to VPS IP (13.53.125.194)
- SSH access to VPS as user with sudo privileges (script assumes 'ubuntu' user)
- Git repository access
- Firebase Service Account JSON file
- OneSignal API key
- Database URL (PostgreSQL, e.g., from Neon)
- Redis URL (e.g., from Upstash)

## Manual Preparation Steps

### 1. Provision and Configure VPS
- Launch Ubuntu VPS instance
- Ensure SSH key-based authentication is set up
- Update DNS records to point sugarmummiesug.online and www.sugarmummiesug.online to 13.53.125.194

### 2. Clone Repository
```bash
cd ~
git clone <repository-url> mazale-django-backend
cd mazale-django-backend
```

### 3. Set Up Environment Variables
Copy the example environment file and edit it with actual values:
```bash
cp .env.example .env
nano .env  # or your preferred editor
```

Required environment variables:
- `DEBUG=False`
- `SECRET_KEY=<your-secure-secret-key>`
- `ALLOWED_HOSTS=sugarmummiesug.online,13.53.125.194,www.sugarmummiesug.online`
- `DATABASE_URL=<postgresql-connection-string>`
- `ONESIGNAL_API_KEY=<your-onesignal-api-key>`

### 4. Place Firebase Service Account File
Ensure `Service-Account.json` is in the project root directory.

## DNS Configuration Requirement

**Important:** Before running the deployment script, ensure that your DNS records are properly configured and have propagated. The domain `sugarmummiesug.online` and `www.sugarmummiesug.online` must point to the VPS IP `13.53.125.194`. DNS propagation can take up 24-48 hours. You can verify DNS propagation using tools like `dig` or online DNS checkers. The deployment script will attempt to obtain SSL certificates, which will fail if DNS is not correctly set up.

## Using the Deploy Script

The `deploy.sh` script automates most of the deployment process. Run it with sudo:

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

### What the Script Does

1. **System Updates**: Updates Ubuntu packages
2. **Install Dependencies**: Installs Python, pip, venv, Nginx, Certbot
3. **Virtual Environment**: Creates and activates Python virtual environment
4. **Install Python Packages**: Upgrades pip and setuptools for compatibility, then installs requirements and Gunicorn
5. **Database Migration**: Runs Django migrations
6. **Static Files**: Collects static files
7. **Gunicorn Service**: Creates systemd service for Gunicorn
8. **Nginx Configuration**: Configures Nginx reverse proxy with SSL
9. **SSL Certificate**: Obtains Let's Encrypt certificate for the domain

## Post-Deployment Steps

### 1. Verify Services
Check that services are running:
```bash
sudo systemctl status mazale
sudo systemctl status nginx
```

### 2. Check Logs
Monitor logs for any issues:
```bash
sudo journalctl -u mazale -f
sudo tail -f /var/log/nginx/error.log
```

### 3. Test Application
Test the application at:
- https://sugarmummiesug.online
- https://www.sugarmummiesug.online
- http://13.53.125.194 (HTTP only, no SSL for IP)

### 4. Set Up Celery (if needed)
If background tasks are required, create similar systemd services for Celery worker and beat.

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure files are owned by the correct user
2. **Database Connection**: Verify DATABASE_URL is correct
3. **Static Files**: Run `python manage.py collectstatic` if static files aren't loading
4. **SSL Issues**: Check certbot logs if SSL certificate fails

### Firewall Configuration
Ensure ports 80 and 443 are open:
```bash
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Security Considerations

- Keep SECRET_KEY secure and unique
- Use strong passwords for database
- Regularly update system packages
- Monitor logs for suspicious activity
- Consider setting up fail2ban for SSH protection

## Maintenance

- **Updates**: Pull latest code and restart services
- **Backups**: Regularly backup database and media files
- **Monitoring**: Set up monitoring for uptime and performance