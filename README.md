# E-commerce API

FastAPI asosida tuzilgan internet-do‘kon backend’i. API’ni `/docs` manzilidagi Swagger orqali tekshirish mumkin. Pul qiymatlari `Decimal/Numeric` bilan saqlanadi; haqiqiy to‘lovlarda ishlatishdan oldin valyuta va to‘lov provayderini belgilang. Dasturlash tili va framework talab qiladigan nomlar, ma’lumotlar bazasi ustunlari, JSON maydonlari, muhit o‘zgaruvchilari hamda topshiriqdagi API yo‘llari integratsiya buzilmasligi uchun standart holatda qoldirilgan.

## Imkoniyatlar va ruxsatlar

- Xaridor ro‘yxatdan o‘tadi, tizimga kiradi, shaxsiy profilini, savatini va buyurtmalarini ko‘radi.
- Administrator kategoriya va mahsulotlarni boshqaradi. Oddiy ro‘yxatdan o‘tish administrator rolini bermaydi.
- Parollar Argon2 bilan xeshlanadi. JWT tokenining muddati sozlanadi.
- Kategoriya va mahsulotlarni ko‘rish ochiq; boshqa xaridorning buyurtmasi maxfiylik uchun `404` qaytaradi.
- Kategoriya, mahsulot va buyurtmalar ro‘yxatlarida sahifalash mavjud. Mahsulotlar nomi, kategoriya va narx bo‘yicha filtrlanadi.
- Buyurtma vaqtida narx va nom nusxasi saqlanadi. Ombor qoldig‘i atomik yangilanadi; qoldiq yetmasa butun xarid rollback qilinadi va savat saqlanadi.
- Buyurtma tarixida qatnashgan mahsulot va mahsuloti bor kategoriya o‘chirilmaydi.

## Mahalliy o‘rnatish

Kerakli vositalar: Python 3.11+, PostgreSQL 14+ va Git.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` ichida PostgreSQL manzili va yangi, tasodifiy `SECRET_KEY` kiriting. Maxfiy kalit yaratish:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Yangi mahalliy PostgreSQL o‘rnatmasida administrator sifatida `postgres` bazasiga ulaning (pgAdmin yoki `psql`) va ilova uchun alohida foydalanuvchi hamda baza yarating. Parolni o‘zingiz tanlang:

```sql
CREATE ROLE ecommerce_user LOGIN PASSWORD 'kuchli-maxfiy-parol';
CREATE DATABASE ecommerce OWNER ecommerce_user;
```

Tanlangan parolni `.env` dagi `DATABASE_URL` ga kiriting; `@`, `/`, `:` va `#` kabi belgilar URL-encode qilinishi kerak. `.env` Git’ga kiritilmaydi va hech kimga yuborilmaydi.

Migratsiyani qo‘llang, administrator yarating va API’ni ishga tushiring:

```powershell
alembic upgrade head
python -m app.create_admin --email admin@example.com
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Swagger: `http://127.0.0.1:8001/docs`; sog‘liq tekshiruvi: `http://127.0.0.1:8001/health`.

## Muhit o‘zgaruvchilari

| O‘zgaruvchi | Vazifasi |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy ulanish manzili, masalan `postgresql+psycopg://foydalanuvchi:parol@localhost:5432/baza` |
| `TEST_DATABASE_URL` | Alohida PostgreSQL test bazasi; berilmasa xotiradagi SQLite ishlatiladi |
| `SECRET_KEY` | JWT imzolash maxfiy kaliti; Git’ga yoki chatga yubormang |
| `ALGORITHM` | JWT algoritmi; standart qiymati `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token amal qilish vaqti, daqiqalarda |
| `APP_NAME`, `APP_VERSION`, `DEBUG` | FastAPI nomi, versiyasi va debug holati |

Maxfiy qiymatlarni faqat mahalliy `.env`, serverdagi himoyalangan muhit fayli yoki GitHub Actions Secrets’da saqlang.

## Swagger orqali namuna

1. `POST /auth/register` ga yuboring:
   ```json
   {"email":"xaridor@example.com","password":"kuchli-parol"}
   ```
2. `POST /auth/login` orqali token oling va Swagger’dagi **Authorize** oynasiga kiriting.
3. Administrator tokeni bilan `POST /categories`, keyin `POST /products` orqali katalog yarating.
4. Xaridor tokeni bilan `/cart/items` ga `{"product_id":1,"quantity":2}` yuboring va `GET /cart` bilan savatni ko‘ring.
5. `POST /orders` buyurtma beradi; natijani `GET /orders` yoki `GET /orders/{order_id}` orqali tekshiring.

Kategoriyalar va mahsulotlarni yozish/o‘chirish uchun administrator tokeni talab qilinadi. `python -m app.create_admin --email ...` parolni terminalda yashirin so‘raydi va faqat yangi administrator yaratadi; mavjud hisobning rolini o‘zgartirmaydi.

## Tuzilma, migratsiya va testlar

- `app/models` — SQLAlchemy jadvallari, bog‘lanishlar va cheklovlar.
- `app/schemas` — Pydantic kirish/chiqish tekshiruvlari.
- `app/routers` — HTTP endpointlar va ruxsat tekshiruvlari.
- `app/services` — savat va buyurtmaning biznes qoidalari.
- `app/dependencies` — JWT foydalanuvchisi va DB sessiyasi.
- `alembic/versions` — ma’lumotlar bazasi migratsiyalari.

```powershell
alembic upgrade head
alembic revision --autogenerate -m "sxema o‘zgarishini izohla"
pytest -q
ruff check app tests alembic
```

Testlar `TEST_DATABASE_URL` berilmasa alohida, xotiradagi SQLite’da ishlaydi. PostgreSQL’da tekshirish uchun alohida test bazasi bering; **testlar jadvallarni yaratib, yakunda o‘chiradi**, shuning uchun unda kerakli ma’lumot saqlamang. GitHub Actions alohida PostgreSQL servisida bo‘sh bazaga migratsiyani qo‘llab, lint va testlarni bajaradi. Test muvaffaqiyatsiz bo‘lsa deploy boshlanmaydi. Parallel checkout testi PostgreSQL tranzaksiyalarini tekshiradi.

## GitHub Actions va AWS EC2

Loyihani GitHub’ga joylang va repozitoriya **Settings → Secrets and variables → Actions** bo‘limida quyidagi secrets’larni yarating:

- `EC2_HOST` — EC2 public DNS yoki IP.
- `EC2_KNOWN_HOSTS` — tekshirilgan SSH host key qatori.
- `EC2_USER` — SSH deploy foydalanuvchisi.
- `EC2_SSH_KEY` — shu foydalanuvchining SSH private key’i.
- `EC2_DEPLOY_PATH` — serverdagi ilova yo‘li, odatda `/opt/ecommerce-api`.

Pull request va `main` push lint, PostgreSQL migratsiyasi va testlarni ishga tushiradi. Faqat muvaffaqiyatli `main` tekshiruvidan so‘ng deploy bajariladi: kod ko‘chiriladi, kutubxonalar o‘rnatiladi, migratsiya qo‘llanadi, systemd xizmat qayta ishga tushadi va ichki hamda Nginx orqali `/health` tekshiriladi. EC2’da PostgreSQL tarmoq orqali ulanishi, Python, Nginx va `rsync` o‘rnatilgan bo‘lishi kerak. PostgreSQL portini internetga ochmang; SSH ulanishini faqat ishonchli IP manzillari bilan cheklang.

### EC2 serverida bir martalik sozlash (Ubuntu)

`ecommerce` xizmat foydalanuvchisini yarating, PostgreSQL’ni sozlang va `/etc/ecommerce-api.env` faylini `root` egasi hamda `600` ruxsati bilan yarating. Faylga production `DATABASE_URL` va yangi `SECRET_KEY` kiriting. Deploy foydalanuvchisiga faqat ilova papkasiga yozish hamda kerakli ikkita systemd amalini `sudo` bilan bajarish huquqini bering.

```bash
sudo cp deploy/systemd/ecommerce-api.service /etc/systemd/system/ecommerce-api.service
sudo cp deploy/systemd/ecommerce-api-migrate.service /etc/systemd/system/ecommerce-api-migrate.service
sudo cp deploy/nginx/ecommerce-api.conf /etc/nginx/sites-available/ecommerce-api
if [ -L /etc/nginx/sites-enabled/default ]; then sudo unlink /etc/nginx/sites-enabled/default; fi
sudo ln -s /etc/nginx/sites-available/ecommerce-api /etc/nginx/sites-enabled/ecommerce-api
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable ecommerce-api nginx
sudo systemctl enable --now nginx
```

`/opt/ecommerce-api/.venv` muhitini Python 3.11+ bilan oldindan yarating va deploy foydalanuvchisiga loyihani yangilash huquqini bering. `EC2_DEPLOY_PATH` qiymati `/opt/ecommerce-api` bilan mos bo‘lsin. `sudoers` orqali faqat `systemctl start ecommerce-api-migrate` va `systemctl restart ecommerce-api` buyruqlariga ruxsat bering. Domen va TLS’ni (masalan, Certbot bilan) sozlang; xavfsizlik guruhida faqat kerakli HTTP/HTTPS trafikni oching.

Nginx sozlamasi `deploy/nginx/ecommerce-api.conf` faylida; ilova va migratsiya uchun doimiy systemd xizmatlari `deploy/systemd/` papkasida.

> Repozitoriydagi fayllar va CI/CD namunasi jonli deploy qilinganini anglatmaydi. GitHub Actions secrets, AWS EC2, domen/TLS va muvaffaqiyatli workflow ishga tushishini alohida sozlab, tekshirish zarur.
