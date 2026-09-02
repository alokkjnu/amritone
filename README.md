# Amrit One — E-Commerce Platform

**Pure. Natural. Authentic.**

A production-ready, enterprise-grade e-commerce platform for Amrit One Organic Food & Ayurvedic Products, built with VayuAPI (Python async framework), Jinja2 templates, PostgreSQL, and SQLAlchemy.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | VayuAPI (Python Async Framework) |
| Templating | Jinja2 |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 (Async) |
| Migrations | Alembic |
| Auth | JWT + Refresh Tokens |
| PDF | ReportLab |
| Images | Pillow (WebP optimisation) |
| Email | aiosmtplib |
| Icons | Font Awesome 6.4 (CDN) |
| Fonts | Lora (serif) + Jost (sans) via Google Fonts |
| Server | Uvicorn + Gunicorn |
| Reverse Proxy | Nginx |
| Containerisation | Docker + Docker Compose |

---

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env with your database, email, and secret settings
```

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

### 3. Run migrations (first time only)

```bash
docker-compose exec app alembic -c migrations/alembic.ini upgrade head
```

The application automatically seeds:
- Default roles (`super_admin`, `admin`, `inventory_manager`, `order_manager`, `customer_support`, `customer`)
- Super admin account (email/password from `.env`)
- 5 initial products with variants
- 3 categories

### 4. Access the application

| URL | Description |
|---|---|
| `http://localhost` | Customer storefront |
| `http://localhost/admin` | Admin portal |
| `http://localhost/login` | Customer login |

**Default admin:** `admin@amritone.in` / `Admin@123` *(change immediately in production!)*

---

## Project Structure

```
amritone_in/
├── main.py                   # Application entry point
├── config/
│   ├── settings.py           # Environment-based configuration
│   ├── database.py           # Async SQLAlchemy engine & session
│   └── templates.py          # Jinja2 env with custom filters
├── models/                   # SQLAlchemy ORM models
├── schemas/                  # Pydantic validation schemas
├── repositories/             # Database query layer
├── services/                 # Business logic layer
├── controllers/              # Route handlers (VayuAPI routers)
├── middlewares/              # Auth, security, audit, rate limiting
├── templates/
│   ├── base.html             # Root layout (FontAwesome + main.css + main.js)
│   ├── admin/
│   │   ├── base.html         # Admin layout (sidebar nav, topbar, role guards)
│   │   ├── dashboard.html    # Stats overview + recent orders + low-stock alert
│   │   ├── products/         # Product list + create/edit form
│   │   ├── categories/       # Category CRUD
│   │   ├── orders/           # Order list + detail
│   │   ├── inventory/        # Stock management
│   │   ├── coupons/          # Coupon CRUD
│   │   ├── customers/        # Customer list + detail
│   │   ├── banners/          # Hero banner management
│   │   ├── blogs/            # Blog CMS
│   │   ├── reviews/          # Review moderation
│   │   ├── returns/          # Return requests
│   │   ├── newsletter/       # Subscriber list
│   │   ├── media/            # Media manager
│   │   ├── reports/          # Sales & inventory reports
│   │   ├── audit/            # Audit logs (super_admin only)
│   │   └── settings/         # Site settings (super_admin only)
│   ├── shop/
│   │   ├── home.html         # Homepage (carousel, categories, products, FAQ)
│   │   ├── catalog.html      # Shop with sidebar filters + sort + pagination
│   │   ├── product_detail.html # PDP with gallery, variants, tabs, related
│   │   ├── cart.html         # Shopping cart + coupon
│   │   ├── checkout.html     # Checkout with address + payment
│   │   ├── blog/             # Blog list + detail
│   │   └── account/          # Dashboard, orders, profile, addresses, wishlist
│   ├── auth/                 # Login, register, verify email, forgot/reset password
│   ├── components/
│   │   ├── navbar.html       # Responsive header (top-banner, nav, cart, user menu)
│   │   ├── footer.html       # Footer with columns, social links, newsletter
│   │   ├── product_card.html # Reusable product card (badges, variants, add-to-cart)
│   │   ├── account_sidebar.html
│   │   └── flash_messages.html
│   ├── email/                # Transactional email templates
│   └── errors/               # 404, 500 pages
├── static/
│   ├── css/main.css          # Complete design system (1400+ lines)
│   ├── js/main.js            # Client-side: Auth, Cart, API, flash, variants
│   ├── images/               # Logo and static assets
│   └── uploads/              # User-uploaded media
├── utils/                    # Security, email, image, OTP, PDF helpers
├── migrations/               # Alembic migration scripts
├── tests/                    # Unit and integration tests
├── scripts/                  # backup.sh, migrate.sh
├── Dockerfile
├── docker-compose.yml
└── nginx/nginx.conf
```

---

## UI Design System

The frontend uses a custom CSS design system (`static/css/main.css`) with:

| Token | Value |
|---|---|
| Primary green | `rgb(28, 149, 72)` |
| Accent gold | `#d0904a` |
| Heading font | Lora (serif) |
| Body font | Jost (sans-serif) |
| Icon library | Font Awesome 6.4 |

### Key CSS Components

- **Layout**: `.container`, `.shop-layout`, `.admin-layout`, `.account-layout`, `.catalog-layout`
- **Product cards**: `.product-card`, `.product-img-wrapper`, `.product-info-wrapper`, `.product-badges`, `.btn-add`
- **Hero carousel**: `.hero-carousel-container`, `.carousel-slide`, `.carousel-prev/next`, `.dot`
- **Buttons**: `.btn`, `.btn-primary`, `.btn-outline`, `.btn-gold`, `.btn-sm`, `.btn-lg`, `.btn-full`
- **Forms**: `.form-group`, `.form-label`, `.form-input`
- **Admin**: `.admin-sidebar`, `.admin-card`, `.data-table`, `.stat-card`, `.stats-grid`
- **Status badges**: `.status-badge .status-{pending|confirmed|shipped|delivered|cancelled|paid|...}`
- **Flash messages**: `.flash-container`, `.flash-{success|error|info|warning}`

### JavaScript (`static/js/main.js`)

Client-side modules:
- **`Auth`** — JWT token management (`getToken`, `setTokens`, `clearTokens`, `isLoggedIn`)
- **`apiFetch`** — Authenticated fetch with automatic token refresh on 401
- **`Cart`** — `add`, `update`, `remove`, `updateBadge`, `refreshBadge`
- **`showFlash`** — Toast notification system
- **`initVariantSelection`** — Product card variant switching (`.card-size-btn`)
- **`initAddToCart`** — Delegated add-to-cart for `.add-to-cart-btn` and `.btn-add`
- **`initHamburger`** — Responsive nav toggle (`.mobile-active` on `#main-header`)
- **`initLogout`** — Delegated logout for all `#logout-btn` elements
- **`initCartPage`** — Cart page quantity controls
- **`initCouponForm`** — Coupon apply/remove
- **`initNewsletterForms`** — Newsletter subscription
- **`toggleWishlist`** — Wishlist add/remove via API

---

## Features

### Customer Storefront
- Registration, login, email verification (OTP), password reset
- JWT authentication with automatic refresh token rotation
- Product catalog with search, filter by category, sort, and pagination
- Product detail page: image gallery, variant selection, tabs (description / ingredients / benefits / usage), related products
- Shopping cart with quantity controls and coupon codes
- Checkout with billing/shipping address and COD / UPI payment
- Order history, order detail, invoice PDF download, tracking number
- Wishlist, saved addresses, profile management
- Return & cancellation request flow
- Newsletter subscription

### Admin Portal
- Dashboard: revenue stats (daily / monthly / total), low-stock alerts, pending reviews
- Role-based navigation (super_admin / admin / inventory_manager / order_manager / customer_support)
- Full product & variant CRUD (unlimited products, multiple size variants)
- Category, inventory, coupon (percentage & flat), and banner management
- Order management with status workflow and PDF invoice generation
- Customer management with account activation / deactivation
- Blog CMS with draft / publish workflow and category tagging
- Review moderation (approve / reject)
- Media manager with server-side WebP optimisation
- Newsletter subscriber list export
- Returns & refund management
- Sales, revenue, and inventory reports
- Audit logs (super_admin only)
- Site settings (super_admin only)

### SEO
- Semantic, SEO-friendly URLs with slug-based routing
- Per-page `<meta>` description, keywords, canonical URL
- Open Graph and Twitter Card tags on all pages
- Schema.org structured data (Product, Organization)
- Auto-generated `sitemap.xml` and `robots.txt`

### Security
- bcrypt password hashing (cost 12)
- JWT access + refresh tokens with rotation on every refresh
- CSRF protection via SameSite cookies
- Per-IP sliding-window rate limiting
- Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- SQL injection protection via SQLAlchemy ORM
- XSS protection via Jinja2 auto-escaping
- Role-based access control on every admin route

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Database Backup

```bash
./scripts/backup.sh
```

Backups are stored in `./backups/` with automatic 30-day retention.

---

## Environment Variables

See `.env.example` for all required configuration keys (database URL, secret key, SMTP, company details, etc.).

---

## Deployment

Production deployment uses Docker Compose with Nginx as a reverse proxy.

```bash
docker-compose -f docker-compose.yml up -d --build
```

For SSL, use Let's Encrypt:

```bash
certbot certonly --nginx -d amritone.in -d www.amritone.in
```

See `docker-compose.yml` and `nginx/nginx.conf` for the full production configuration.

---

*Built with VayuAPI — Pure. Natural. Authentic.*

