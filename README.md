# E-commerce API

FastAPI backend for product catalog, customer carts, stock-safe checkout, and order history. The API is browsable at `/docs`; all prices are decimal amounts in the configured currency (set and document the currency before using real payments).

## Features and access

- Customers can register, log in, inspect their own profile/cart/orders, and checkout.
- Admins can manage categories and products. Registration always creates a `customer`; it never accepts a role.
- Passwords are Argon2-hashed. JWT access tokens expire after the configured number of minutes.
- Product and category reads are public. Customer-owned orders are returned as 404 when requested by another customer.
- Pagination is available on catalog/category/order lists; catalog filters include name, category, and price bounds.
- Checkout snapshots item names and prices, validates/decrements stock with a conditional database update, and clears the cart in the same transaction. Any shortage rolls the entire checkout back.
- Products referenced by order history cannot be deleted; categories with products cannot be deleted.

## Local setup

Requirements: Python 3.11+, PostgreSQL 14+, and Git.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with a real PostgreSQL URL and a unique random `SECRET_KEY` (for example, generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Create a local PostgreSQL database and user, then apply migrations and start the server:

```powershell
alembic upgrade head
python -m app.create_admin --email admin@example.com
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`; health check: `http://127.0.0.1:8000/health`.

For a new local PostgreSQL installation, connect to database `postgres` as a PostgreSQL administrator (pgAdmin or `psql`) and create a dedicated application role and database:

```sql
CREATE ROLE ecommerce_user LOGIN PASSWORD 'choose-a-strong-password';
CREATE DATABASE ecommerce OWNER ecommerce_user;
```

Set the chosen password in the `.env` `DATABASE_URL` (URL-encode reserved characters) and replace the example signing key with a generated random secret. The `.env` file is ignored by Git and must not be shared.

## Environment variables

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `postgresql+psycopg://user:password@host:5432/database` |
| `TEST_DATABASE_URL` | Optional separate PostgreSQL test database URL; unset uses isolated in-memory SQLite |
| `SECRET_KEY` | Private JWT signing secret; never commit or reuse the sample value |
| `ALGORITHM` | JWT algorithm; default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime; default `30` |
| `APP_NAME`, `APP_VERSION`, `DEBUG` | FastAPI metadata and debug mode |

All secrets belong in local `.env`, deployment secret storage, or the EC2 environment file, not Git.

## API quick start

1. `POST /auth/register`
   ```json
   {"email":"buyer@example.com","password":"strong-password"}
   ```
2. `POST /auth/login` with the same JSON; copy `access_token` and use `Authorization: Bearer <token>`.
3. Admin adds a category with `POST /categories`, then a product with `POST /products`.
4. Customer adds `{ "product_id": 1, "quantity": 2 }` to `POST /cart/items` and reads `GET /cart`.
5. `POST /orders` checks stock and returns the order with checkout-time unit prices. Read history via `GET /orders` and `GET /orders/{order_id}`.

Admin write operations require an admin bearer token. `python -m app.create_admin --email ...` prompts for a password and only creates a new admin; it will not promote an existing customer. Use it only on a trusted machine/server with database access.

## Database and tests

Models are in `app/models`, request/response schemas in `app/schemas`, HTTP endpoints in `app/routers`, and authentication/DB dependencies in `app/dependencies` and `app/db`. Alembic owns schema changes:

```powershell
alembic upgrade head
alembic revision --autogenerate -m "describe schema change"
pytest -q
ruff check app tests alembic
```

Tests use isolated in-memory SQLite for fast local execution unless `TEST_DATABASE_URL` is set. Never point it at a database containing data you need: tests create and drop their tables. GitHub Actions uses a dedicated PostgreSQL test database, applies Alembic migrations to it, runs Ruff and the API tests, and blocks deployment on any failure. The conditional stock decrement is atomic in PostgreSQL and prevents two buyers from overselling the same remaining units.

## GitHub Actions and EC2 deployment

Create a public or teacher-accessible GitHub repository, push this project to its `main` branch, and configure these repository Actions secrets:

- `EC2_HOST`: public EC2 DNS name or IP.
- `EC2_KNOWN_HOSTS`: verified SSH host-key line for the EC2 host.
- `EC2_USER`: SSH deployment user.
- `EC2_SSH_KEY`: private key matching the EC2 user's authorized key.
- `EC2_DEPLOY_PATH`: application path, normally `/opt/ecommerce-api`.

The test job runs on pull requests and main pushes. Only a successful main push runs deployment. The workflow copies source (excluding `.env` and virtualenv), installs dependencies, migrates, restarts systemd, and checks Nginx `/health`. The EC2 instance must already have PostgreSQL reachable, the environment file/database configured, the deployment user authorized for passwordless restart of `ecommerce-api`, and `rsync`, Python, and Nginx installed. Restrict SSH ingress to trusted IPs; do not expose PostgreSQL publicly.

### EC2 one-time service setup (Ubuntu)

Create a dedicated `ecommerce` service user, provision PostgreSQL and `/etc/ecommerce-api.env` (permissions `600`, owned by root), and use a deploy account that can write to the app directory and run only the needed systemctl command via sudoers. Set `DATABASE_URL` and a generated `SECRET_KEY` in the environment file.

Install the app and migration services and proxy:

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

Create `/opt/ecommerce-api/.venv` using Python 3.11+, ensure the deploy user can update that directory, and set up Nginx/EC2 security groups for HTTP/HTTPS. Set `EC2_DEPLOY_PATH` to `/opt/ecommerce-api` to match both systemd units. Configure the deployment user's sudoers allow-list for only `systemctl start ecommerce-api-migrate` and `systemctl restart ecommerce-api`; this lets CI run migration and restart without reading the root-protected environment file. The first successful GitHub Actions main deployment applies the initial Alembic migration through the one-shot service and starts the app. Configure TLS (for example, with Certbot) and an appropriate DNS name before production.

The project files and workflow are deployment-ready templates, not proof of a live service: a GitHub repository, configured secrets, AWS account/EC2 instance, DNS/TLS, and successful Actions run must still be supplied and verified for the exam acceptance condition.
