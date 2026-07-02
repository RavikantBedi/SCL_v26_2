# Deploying SCL Automation on a Dedicated Ubuntu VM (Offline Capable)

This guide provides step-by-step instructions for deploying the **SCL Automation** application on a **dedicated Ubuntu VM** that has **very limited internet access**.

Since this is a dedicated VM for this application, we will deploy it professionally on standard web paths (`/var/www/`) and the standard HTTP port (`80`) using Apache as a reverse proxy.

---

## Phase 1: Pre-downloading Dependencies (On a PC WITH Internet)

If your server has no internet or heavily restricted internet, you must download the Python packages on your personal computer first.

1. On your personal PC (must have the same Python version, e.g., 3.10), clone the repo and open a terminal.
2. Run the following command to download all `.whl` package files into a folder without installing them:
   ```bash
   mkdir scl_offline_packages
   pip download -r requirements.txt -d ./scl_offline_packages
   ```
3. Zip the `scl_offline_packages` folder and your project folder, and transfer them to the Ubuntu server via WinSCP, FileZilla, or a USB drive.

---

## Phase 2: Server Setup

### Step 1: Install System Dependencies
If your VM has *brief* internet access, install the required OS packages:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv apache2
```

### Step 2: Get the Project Files onto the Server
Since this is a dedicated VM, it is best practice to host web applications in `/var/www/`.

**Option A: Clone via GitHub (If you have basic internet access)**
```bash
# Navigate to the web directory
cd /var/www/

# Clone the repository directly into a folder named SCL_v26
sudo git clone https://github.com/RavikantBedi/SCL_v26_2.git SCL_v26

# (Optional) If using offline packages, transfer your zipped packages via USB/SCP and move them:
# sudo mv /path/to/transferred/scl_offline_packages /var/www/scl_offline_packages
```

**Option B: Manual Transfer (If you have ZERO internet access)**
```bash
# Assuming you transferred the zipped project folder via USB or SCP
# Move your transferred project folder to /var/www/ and rename it to SCL_v26
sudo mv /path/to/transferred/SCL_v25 /var/www/SCL_v26

# Move your offline packages folder here as well
sudo mv /path/to/transferred/scl_offline_packages /var/www/scl_offline_packages
```

**Assign Permissions (Required for both options):**
```bash
# Assign ownership to the standard Apache web user
sudo chown -R www-data:www-data /var/www/SCL_v26
```

### Step 3: Setup the Virtual Environment
```bash
cd /var/www/SCL_v26

# Create virtual environment 
sudo python3 -m venv venv

# If your server has BRIEF internet:
sudo ./venv/bin/pip install -r requirements.txt

# IF your server has NO internet (using the packages you transferred):
sudo ./venv/bin/pip install --no-index --find-links /var/www/scl_offline_packages -r requirements.txt

# Correct permissions again in case sudo pip changed them
sudo chown -R www-data:www-data /var/www/SCL_v26
```

---

## Phase 3: Background Service (Systemd)

We will configure `systemd` to run the Uvicorn application server continuously in the background.

```bash
sudo nano /etc/systemd/system/SCL_v26.service
```

Paste the following:

```ini
[Unit]
Description=SCL Automation FastAPI Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/SCL_v26
Environment="PATH=/var/www/SCL_v26/venv/bin"
# Run Uvicorn on localhost port 8000
ExecStart=/var/www/SCL_v26/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# Auto-restart if the application crashes
Restart=always

[Install]
WantedBy=multi-user.target
```

Start the service and enable it to run on server boot:
```bash
sudo systemctl daemon-reload
sudo systemctl start SCL_v26
sudo systemctl enable SCL_v26
```

---

## Phase 4: Apache Reverse Proxy

We will configure Apache to serve this application on the standard HTTP port (80) and forward traffic to our hidden Python backend.

### Step 1: Enable Apache Modules
```bash
sudo a2enmod proxy proxy_http headers
```

### Step 2: Create the Virtual Host
```bash
sudo nano /etc/apache2/sites-available/SCL_v26.conf
```

Paste the following:
```apache
<VirtualHost *:80>
    ServerName your_domain_or_IP

    ErrorLog ${APACHE_LOG_DIR}/scl_error.log
    CustomLog ${APACHE_LOG_DIR}/scl_access.log combined

    RequestHeader set X-Forwarded-Proto "http"
    
    # Proxy traffic to our Uvicorn service on port 8000
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Security Headers
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
</VirtualHost>
```

### Step 3: Enable the Site & Reload
Since this is a dedicated VM, we want to disable Apache's default welcome page so our application takes full priority:
```bash
sudo a2dissite 000-default.conf
sudo a2ensite SCL_v26.conf
sudo systemctl restart apache2
```

---

## Phase 5: Accessing the App

Open your web browser and navigate to your VM's IP address:
`http://your_server_ip/`

If you encounter any issues:
- Check Apache logs: `sudo tail -f /var/log/apache2/scl_error.log`
- Check Uvicorn backend logs: `sudo journalctl -u SCL_v26.service -f`
