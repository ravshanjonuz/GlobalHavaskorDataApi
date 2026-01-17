#!/bin/bash
# GlobalTest DATA API - Server O'rnatish Skripti
# Server: 159.69.189.47
# Domain: globalhavaskor.uz

set -e

echo "=========================================="
echo "GlobalTest DATA API O'rnatish"
echo "=========================================="

# 1. Kerakli paketlarni o'rnatish
echo "[1/8] Paketlarni o'rnatish..."
apt update
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git tmux

# 2. Papka yaratish
echo "[2/8] Papkalar yaratish..."
mkdir -p /var/www/globaltest
cd /var/www/globaltest

# 3. GitHub dan clone qilish
echo "[3/8] GitHub dan yuklab olish..."
if [ -d ".git" ]; then
    git pull
else
    git clone https://github.com/ravshanjonuz/GlobalTest.git .
fi

# 4. Virtual environment
echo "[4/8] Python virtual environment..."
cd /var/www/globaltest/DataAPI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Environment faylini yaratish
echo "[5/8] Environment sozlash..."
cat > /var/www/globaltest/DataAPI/.env << 'EOF'
DATA_FILE=/var/www/globaltest/data.zip
DATABASE=/var/www/globaltest/licenses.db
API_SECRET=GlobalTest2024SecretKey159
EOF

# 6. Nginx konfiguratsiya
echo "[6/8] Nginx sozlash..."
cat > /etc/nginx/sites-available/globaltest-api << 'EOF'
server {
    listen 80;
    server_name globalhavaskor.uz www.globalhavaskor.uz;

    location /api {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        client_max_body_size 500M;
    }

    location / {
        return 200 'GlobalTest API Server';
        add_header Content-Type text/plain;
    }
}
EOF

ln -sf /etc/nginx/sites-available/globaltest-api /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 7. SSL sertifikat
echo "[7/8] SSL sertifikat o'rnatish..."
certbot --nginx -d globalhavaskor.uz -d www.globalhavaskor.uz --non-interactive --agree-tos --email admin@globalhavaskor.uz || true

# 8. Tmux da API ni ishga tushirish
echo "[8/8] API ni tmux da ishga tushirish..."
cd /var/www/globaltest/DataAPI
source venv/bin/activate

# Eski tmux sessiyasini to'xtatish
tmux kill-session -t globaltest-api 2>/dev/null || true

# Yangi tmux sessiya yaratish
tmux new-session -d -s globaltest-api "cd /var/www/globaltest/DataAPI && source venv/bin/activate && python app.py"

echo ""
echo "=========================================="
echo "O'rnatish tugadi!"
echo "=========================================="
echo ""
echo "API URL: https://globalhavaskor.uz/api/health"
echo "API Secret: GlobalTest2024SecretKey159"
echo ""
echo "Tmux sessiyasini ko'rish: tmux attach -t globaltest-api"
echo "Tmux dan chiqish: Ctrl+B, keyin D"
echo ""
