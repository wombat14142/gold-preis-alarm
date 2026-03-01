import os
import yfinance as yf
import requests

METALS = [
    ("Gold",   "GC=F", 2.0),
    ("Silber", "SI=F", 5.0),
]


def get_price_change(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="5d", interval="1d")
    prices = hist["Close"].dropna()
    if len(prices) < 2:
        return None, None, None
    return prices.iloc[-2], prices.iloc[-1], (prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2] * 100


def send_telegram(message, bot_token, chat_ids):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        response = requests.post(url, json={"chat_id": chat_id, "text": message})
        if not response.ok:
            print(f"Telegram Fehler für {chat_id}: {response.status_code} – {response.text}")
        response.raise_for_status()


def check_metal(name, ticker_symbol, threshold_pct, bot_token, chat_ids):
    price_yesterday, price_now, change_pct = get_price_change(ticker_symbol)

    if price_yesterday is None:
        print(f"Nicht genug Daten für {name}.")
        return

    print(f"{name} gestern:  ${price_yesterday:.2f}")
    print(f"{name} aktuell: ${price_now:.2f}")
    print(f"Veränderung:     {change_pct:+.2f}%")

    if change_pct <= -threshold_pct:
        message = (
            f"{name} Alarm!\n\n"
            f"Der {name}preis ist seit gestern um {change_pct:.1f}% gefallen.\n\n"
            f"Aktuell:  ${price_now:.2f}\n"
            f"Gestern: ${price_yesterday:.2f}"
        )
        send_telegram(message, bot_token, chat_ids)
        print(f"{name} Alarm gesendet!")
    else:
        print(f"Kein {name}-Alarm nötig.")


def send_test_message(bot_token, chat_ids):
    lines = ["Test erfolgreich!\n"]
    for name, ticker_symbol, threshold_pct in METALS:
        price_yesterday, price_now, change_pct = get_price_change(ticker_symbol)
        if price_yesterday is None:
            lines.append(f"{name}: Keine Daten verfügbar")
        else:
            print(f"{name} gestern:  ${price_yesterday:.2f}")
            print(f"{name} aktuell: ${price_now:.2f}")
            print(f"Veränderung:     {change_pct:+.2f}%")
            lines.append(f"{name}: ${price_now:.2f} ({change_pct:+.2f}% seit gestern, Alarm ab -{threshold_pct}%)")
    send_telegram("\n".join(lines), bot_token, chat_ids)
    print("Testnachricht gesendet!")


def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_ids = [os.environ["TELEGRAM_CHAT_ID"]]

    chat_id_2 = os.environ.get("TELEGRAM_CHAT_ID_2", "").strip()
    if chat_id_2:
        chat_ids.append(chat_id_2)

    if os.environ.get("FORCE_TEST", "").lower() == "true":
        send_test_message(bot_token, chat_ids)
    else:
        for name, ticker_symbol, threshold_pct in METALS:
            check_metal(name, ticker_symbol, threshold_pct, bot_token, chat_ids)


if __name__ == "__main__":
    main()
