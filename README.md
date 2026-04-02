# BankToSure 🚀

Automated bridge to sync **Fortuneo** bank transactions into the **Sure** finance platform with smart deduplication and Discord notifications.

## 🏦 Supported Banks

| Bank | Status | Provider |
| :--- | :--- | :--- |
| **Fortuneo** | ✅ Supported | `FortuneoProvider` |

## 🚀 Getting Started

### 1. Setup
Ensure you have [uv](https://astral.sh/uv) installed.
```bash
uv sync
playwright install chromium
```

### 2. Configuration
Create a `.env` file based on your credentials:
```env
FORTUNEO_ID="your_id"
FORTUNEO_PWD="your_password"
SURE_API_KEY="your_api_key"
SURE_ACCOUNT_ID="your_account_id"
SURE_URL="http://localhost:3000"
DISCORD_WEBHOOK_URL="your_webhook_url"
# Optional
SYNC_TIME="09:00"
```

### 3. Usage

**Standard Sync (Last 30 days):**
```bash
uv run main.py
```

**One-time Historical Import (e.g., 1 year):**
```bash
uv run main.py --days 365
```

**Dry Run (Simulate without pushing):**
```bash
uv run main.py --dry-run
```

**Persistent Mode (Stay active and sync daily):**
```bash
uv run main.py --schedule --time 09:30
```

## 🛠️ Architecture
- **Modular**: Add new banks in `src/providers/` or new destinations in `src/destinations/`.
- **Safe**: Built-in deduplication by scanning your entire Sure history before any injection.
- **Robust**: Detailed logging with **Loguru** and typed data with **Pydantic**.
