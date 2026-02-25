# VPN Bot for Marzban

Telegram bot for selling and managing VPN subscriptions via [Marzban](https://github.com/Gozargah/Marzban) panel.

## Features

### User Features
- 🔑 **VPN Management** - Get subscription links and QR codes
- 💰 **Tariff Plans** - Multiple subscription plans with different traffic limits
- 📊 **Status Check** - View traffic usage and expiration date
- 🎁 **Referral System** - Earn bonus days by inviting friends
- 🆓 **Trial Period** - 3-day free trial for new users
- 💳 **Manual Payments** - Simple card payment with admin confirmation

### Admin Features
- 📊 **Statistics** - Bot and Marzban panel statistics
- 💰 **Payment Management** - Approve/reject payment requests
- 👥 **User Management** - Search, view, and manage users
- 🚫 **Ban/Unban** - Control user access
- 📢 **Broadcast** - Send messages to all users
- 🔍 **User Search** - Find users by ID or username

## Project Structure

```
skynetbot_marzban/
├── main.py                 # Main bot entry point
├── marzban_client.py       # Marzban API client
├── database.py             # SQLite database operations
├── handlers_user.py        # User bot handlers
├── handlers_admin.py       # Admin bot handlers
├── background_tasks.py     # Periodic tasks (notifications, cleanup)
├── keyboards.py            # Inline and reply keyboards
├── states.py               # FSM states
├── data/
│   └── tarifs.json         # Tariff plans configuration
├── logs/                   # Bot logs (auto-created)
├── .env.example            # Configuration template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
└── deploy_bot.sh           # Deployment script
```

## Requirements

- Python 3.11+
- Marzban panel (v0.5.0+)
- Telegram Bot Token
- Docker & Docker Compose (optional)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd skynetbot_marzban
```

### 2. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

### Configuration Options

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | ✅ |
| `ADMIN_USER_IDS` | Comma-separated admin Telegram IDs | ✅ |
| `MARZBAN_PANEL_URL` | Your Marzban panel URL | ✅ |
| `MARZBAN_USERNAME` | Marzban admin username | ✅ |
| `MARZBAN_PASSWORD` | Marzban admin password | ✅ |
| `MARZBAN_SUBSCRIPTION_URL_PREFIX` | Subscription URL prefix | ❌ |
| `PAYMENT_CARD_NUMBER` | Card number for payments | ❌ |
| `PAYMENT_CARD_HOLDER` | Card holder name | ❌ |
| `TG_CHANNEL` | Telegram channel link | ❌ |
| `SUPPORT_URL` | Support contact link | ❌ |
| `REF_BONUS_DAYS` | Bonus days per referral | ❌ |
| `VERIFY_SSL` | Verify SSL certificates | ❌ |

### 3. Configure Tariffs

Edit `data/tarifs.json` to customize your tariff plans:

```json
{
    "tariffs": [
        {
            "id": "basic",
            "name": "🥉 Базовый",
            "price": 100,
            "traffic_gb": 100,
            "duration_days": 30,
            "max_ips": 2,
            "is_trial": false
        }
    ]
}
```

### 4. Deploy

#### Option A: Docker (Recommended)

```bash
# Make deployment script executable
chmod +x deploy_bot.sh

# Run deployment
./deploy_bot.sh
```

#### Option B: Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

#### Option C: Docker Compose

```bash
docker-compose up -d
```

## Usage

### User Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/admin` | Open admin panel (admins only) |

### Bot Menu

- 🔑 **Мой VPN** - Manage your VPN subscription
- 💰 **Тарифы** - View and purchase tariff plans
- 📊 **Статус** - Check subscription status
- 🎁 **Рефералы** - Referral program
- ℹ️ **Помощь** - Help and support
- 👤 **Профиль** - User profile

### Admin Commands

| Command | Description |
|---------|-------------|
| `/admin` | Open admin panel |

### Admin Panel

- 📊 **Статистика** - View bot and Marzban statistics
- 💰 **Платежи** - Review and approve payments
- 👥 **Пользователи** - Search and manage users
- 📢 **Рассылка** - Broadcast messages to all users

## Payment Flow

1. User selects a tariff plan
2. Bot displays payment details (card number, comment)
3. User makes manual payment and clicks "Confirm Payment"
4. Admin receives notification
5. Admin reviews and approves/rejects payment
6. User receives notification and subscription is activated

## Background Tasks

The bot runs these tasks automatically:

| Task | Frequency | Description |
|------|-----------|-------------|
| **Expired Check** | Hourly | Remove expired subscriptions |
| **Expiration Notifications** | Hourly | Notify users before expiry (24h, 48h, 72h) |
| **Traffic Sync** | Hourly | Sync traffic usage from Marzban |
| **Payment Cleanup** | Daily | Remove old processed payments |

## Logs

Bot logs are stored in `logs/bot.log`

View Docker logs:
```bash
docker-compose logs -f
```

## Database

The bot uses SQLite database stored in `data/users.db`:

- **users** - User accounts
- **subscriptions** - Active subscriptions
- **payments** - Payment records
- **referrals** - Referral relationships

## Troubleshooting

### Bot doesn't start

1. Check `.env` configuration
2. Verify bot token is valid
3. Check Marzban panel accessibility
4. Review logs: `docker-compose logs`

### Can't connect to Marzban

1. Verify `MARZBAN_PANEL_URL` is correct
2. Check admin credentials
3. Ensure Marzban panel is running
4. Check SSL settings (`VERIFY_SSL`)

### Payments not working

1. Verify `PAYMENT_CARD_NUMBER` is set
2. Ensure admin IDs are correct
3. Check bot has permission to message users

## Security Notes

- ⚠️ **Never commit `.env` file** - Contains sensitive credentials
- ⚠️ **Use HTTPS** for Marzban panel URL
- ⚠️ **Restrict admin access** - Only trusted Telegram IDs
- ⚠️ **Regular backups** - Backup `data/users.db` regularly

## License

This project is provided as-is for educational purposes.

## Support

For issues and feature requests, please create an issue in the repository.

## Credits

- [Marzban](https://github.com/Gozargah/Marzban) - VPN management panel
- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot API framework
- Inspired by [VPN_bot_for_3X-UI](https://github.com/Major-Woolfi/VPN_bot_for_3X-UI)
