import os
import yfinance as yf
import requests


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


def check_metal(name, ticker_symbol, threshold_pct, bot_token, chat_ids, force_test):
    price_yesterday, price_now, change_pct = get_price_change(ticker_symbol)

    if price_yesterday is None:
        print(f"Nicht genug Daten für {name}.")
        return

    print(f"{name} gestern:  ${price_yesterday:.2f}")
    print(f"{name} aktuell: ${price_now:.2f}")
    print(f"Veränderung:     {change_pct:+.2f}%")

    if force_test:
        message = (
            f"Test: {name}\n\n"
            f"Aktuell:  ${price_now:.2f}\n"
            f"Gestern: ${price_yesterday:.2f}\n"
            f"Veränderung: {change_pct:+.2f}%"
        )
        send_telegram(message, bot_token, chat_ids)
        print(f"{name} Testnachricht gesendet!")
    elif change_pct <= -threshold_pct:
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


def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_ids = [os.environ["TELEGRAM_CHAT_ID"]]

    chat_id_2 = os.environ.get("TELEGRAM_CHAT_ID_2", "").strip()
    if chat_id_2:
        chat_ids.append(chat_id_2)

    force_test = os.environ.get("FORCE_TEST", "").lower() == "true"

    check_metal("Gold", "GC=F", 2.0, bot_token, chat_ids, force_test)
    check_metal("Silber", "SI=F", 5.0, bot_token, chat_ids, force_test)


if __name__ == "__main__":
    main()
