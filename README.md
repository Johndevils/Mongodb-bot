# MongoDB Transfer Bot 🤖

A Telegram bot for transferring data between MongoDB collections with deployment monitoring.

## Features

- Secure data transfer between MongoDB instances
- Deployment success notifications
- Web endpoint with custom message
- Health checks
- Environment variable configuration

## Setup

1. Get a Telegram bot token from [@BotFather](https://t.me/BotFather)
2. Clone this repository
3. Install dependencies: `pip install -r requirements.txt`
4. Create `.env` file from `.env.example`
5. Configure environment variables:
   - `TELEGRAM_BOT_TOKEN`: Your bot token
   - `ADMIN_CHAT_ID`: Your Telegram chat ID (get from @userinfobot)
   - `PORT`: Web server port (default: 8080)

## Deployment to Render

1. Create a new Render account
2. Create a new Web Service
3. Use the provided `render.yaml` configuration
4. Set environment variables in Render dashboard
5. Deploy!

## Usage

- Access your Render URL to see "Arsynox Successfully"
- Use these Telegram commands:
  - `/set_source` - Set source MongoDB URI
  - `/set_target` - Set target MongoDB URI
  - `/transfer` - Transfer data between collections

Example MongoDB URI:
`mongodb://user:password@host:27017/database_name`

## Web Endpoints

- `GET /`: Returns "Arsynox Successfully" text response
- Health checks automatically configured for Render
