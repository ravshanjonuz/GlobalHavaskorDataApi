# GlobalTest DATA API - O'rnatish Ko'rsatmasi

## 1. Serverda papka yaratish
```bash
sudo mkdir -p /var/www/globaltest
sudo chown $USER:$USER /var/www/globaltest
cd /var/www/globaltest
```

## 2. Fayllarni yuklash
```bash
# app.py va requirements.txt ni yuklang
scp DataAPI/* user@server:/var/www/globaltest/
```

## 3. Virtual environment yaratish
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. DATA faylini yuklash
```bash
# DATA papkangizni ZIP qiling:
# Windows da: DATA papkasini o'ng tugma -> "Send to" -> "Compressed (zipped) folder"
# Keyin serverga yuklang:
scp data.zip user@server:/var/www/globaltest/
```

## 5. Environment sozlash
```bash
# .env fayl yarating:
cat > .env << EOF
DATA_FILE=/var/www/globaltest/data.zip
DATABASE=/var/www/globaltest/licenses.db
API_SECRET=sizning-maxfiy-kalitingiz-buni-ozgartiring
EOF
```

## 6. Systemd service o'rnatish
```bash
sudo cp globaltest-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable globaltest-api
sudo systemctl start globaltest-api
```

## 7. Nginx sozlash
```bash
sudo cp nginx.conf /etc/nginx/sites-available/globaltest-api
sudo ln -s /etc/nginx/sites-available/globaltest-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL sertifikat (Let's Encrypt)
```bash
sudo certbot --nginx -d globalhavaskor.uz
```

## 9. Test qilish
```bash
# Health check
curl https://globalhavaskor.uz/api/health

# Litsenziya tekshirish
curl "https://globalhavaskor.uz/api/check?compId=TEST-ID&key=TEST-KEY"
```

## 10. KeyGenerator dan litsenziya qo'shish
KeyGenerator dasturidan yangi kalit yaratilganda, API ga avtomatik saqlanadi.

Admin API:
- `POST /api/admin/licenses` - Yangi litsenziya
- `GET /api/admin/licenses` - Barcha litsenziyalar
- `DELETE /api/admin/licenses/{id}` - O'chirish

Header: `X-API-Key: sizning-api-secret-kalit`
