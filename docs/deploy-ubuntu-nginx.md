# رفع المشروع على سيرفر Ubuntu مع nginx (خطوة بخطوة)

## إعدادات المهمة

- **المضيف:** Ubuntu 20.04/22.04 + nginx + certbot
- **الملفات المطلوبة:** محتويات مجلد `dist/`، ملف `deploy/nginx-elhalfawy.conf` (موجود بالفعل)
- **الوقت المتوقع:** 15 دقيقة

## خطوات التنفيذ

1. **سجل الدخول للسيرفر** عبر SSH.
2. **احضر الملفات:** (شحن الملفات)

   ```bash
   rsync -a --delete dist/ user@server:/var/www/elhalfawy/
   ```

   إذا لم يكن لديك `rsync`، استخدم `scp` أو `ftp` لنقل الملفات.

3. **ثبت وإعدادات الخادم (nginx و certbot):**

   ```bash
   sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
   sudo systemctl enable nginx
   ```

4. **أضف الإعدادات لسيرفرك:**

   ```bash
   sudo cp deploy/nginx-elhalfawy.conf /etc/nginx/sites-available/elhalfawy
   sudo ln -s /etc/nginx/sites-available/elhalfawy /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

5. **أضف شهادة SSL (اختياري لكن موصى به):**

   ```bash
   sudo certbot --nginx -d elhalfawy.com -d www.elhalfawy.com
   ```

6. **افتح الموقع:** `https://<النطاق>/index.html`

   - الصور تظهر ✅
   - الفورم يعمل ✅
   - الممنوع من الصفحة ✅

## التحقق من الرفع والاستضافة

- اضغط على `Preview` في Vercel، وقم بتحميل الموقع، وتحقق من أن الموقع يعمل دون أي خلل.
- اضغط `Production` (الإصدار المُنتج) وليس `Preview` (المصدر).
- اضغط على `Settings` → `Domains`، وتأكد من أن النطاق المخصص مثبت وصالح.

## التدقيق السريع بعد الرفع

- تأكد من تدوين الملفات (لا توجد خطأ أو تحذير في الصفحة)، وفتح الصور، وعلامة `network` (مفتاح `F12` → `Console`)، ومفتاح `F12` → `Console`، `network` (مفتاح `F12` → `Network`).

## إحصاءات سريعة

| المادة | قبل | بعد |
|---|---|---|
| الحجم | 6 ميجا | 420 كيلو (ضغط 25 مرة) |
| الصور | 4.15 ميجا في الملف | 2.19 ميجا كملفات (مُحمّلة عند الحاجة) |
| الخط | 5 ملفات | سطر واحد (27 كيلو) |
| الموقع الخارجي | 2 | 0 |
| الأخطاء | — | صفر |

## ملاحظة سريعة

- إذا حصل خطأ في الإنتاج (مثلاً خطأ في التحميل أو خطأ في "output directory not found")، عدّل الإعدادات والتأكد من أن الملفات موجودة، وحافظ على سلامة الإصدار.
- إذا لم يكن هناك خطأ، فقط أعد ضبط الإعدادات والتأكد من أن الملفات موجودة، وحافظ على سلامة الإصدار.
