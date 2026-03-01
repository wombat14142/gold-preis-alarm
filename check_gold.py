import os
import yfinance as yf
import requests


def get_gold_prices():
    ticker = yf.Ticker("GC=F")
    hist = ticker.history(period="8d", interval="1d")
    return hist["Close"].dropna()


def send_telegram(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
    response.raise_for_status()


def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    prices = get_gold_prices()

    if len(prices) < 2:
        print("Nicht genug Daten verfügbar.")
        return

    price_7d_ago = prices.iloc[0]
    price_now = prices.iloc[-1]
    change_pct = (price_now - price_7d_ago) / price_7d_ago * 100

    print(f"Gold vor 7 Tagen: ${price_7d_ago:.2f}")
    print(f"Gold aktuell:     ${price_now:.2f}")
    print(f"Veränderung:      {change_pct:+.2f}%")

    if change_pct <= -2.0:
        message = (
            f"<b>Gold Alarm!</b>\n\n"
            f"Der Goldpreis ist in den letzten 7 Tagen um <b>{change_pct:.1f}%</b> gefallen.\n\n"
            f"Aktuell:       <b>${price_now:.2f}</b>\n"
            f"Vor 7 Tagen: ${price_7d_ago:.2f}"
        )
        send_telegram(message, bot_token, chat_id)
        print("Alarm gesendet!")
    else:
        print("Kein Alarm nötig.")


if __name__ == "__main__":
    main()
