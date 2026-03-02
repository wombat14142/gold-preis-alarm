import os
import yfinance as yf
import requests

METALS = [
    ("Gold",   "XAUUSD=X", "XAUEUR=X", 2.0),
    ("Silber", "XAGUSD=X", "XAGEUR=X", 5.0),
]


def get_price_change(usd_ticker, eur_ticker):
    def fetch(symbol):
        hist = yf.Ticker(symbol).history(period="5d", interval="1d")
        return hist["Close"].dropna()

    usd_prices = fetch(usd_ticker)
    eur_prices = fetch(eur_ticker)

    if len(usd_prices) < 2:
        return None, None, None, None, None

    usd_yesterday, usd_now = usd_prices.iloc[-2], usd_prices.iloc[-1]
    change_pct = (usd_now - usd_yesterday) / usd_yesterday * 100

    eur_yesterday = eur_prices.iloc[-2] if len(eur_prices) >= 2 else None
    eur_now = eur_prices.iloc[-1] if not eur_prices.empty else None

    return usd_yesterday, usd_now, change_pct, eur_yesterday, eur_now


def send_telegram(message, bot_token, chat_ids):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        response = requests.post(url, json={"chat_id": chat_id, "text": message})
        if not response.ok:
            print(f"Telegram Fehler für {chat_id}: {response.status_code} – {response.text}")


def check_metal(name, usd_ticker, eur_ticker, threshold_pct, bot_token, chat_ids):
    usd_yesterday, usd_now, change_pct, eur_yesterday, eur_now = get_price_change(usd_ticker, eur_ticker)

    if usd_yesterday is None:
        print(f"Nicht genug Daten für {name}.")
        return

    eur_now_str = f" / €{eur_now:.2f}" if eur_now else ""
    eur_yesterday_str = f" / €{eur_yesterday:.2f}" if eur_yesterday else ""

    print(f"{name} gestern:  ${usd_yesterday:.2f}{eur_yesterday_str}")
    print(f"{name} aktuell: ${usd_now:.2f}{eur_now_str}")
    print(f"Veränderung:     {change_pct:+.2f}%")

    if change_pct <= -threshold_pct:
        message = (
            f"{name} Alarm!\n\n"
            f"Der {name}preis ist seit gestern um {change_pct:.1f}% gefallen.\n\n"
            f"Aktuell:  ${usd_now:.2f}{eur_now_str}\n"
            f"Gestern: ${usd_yesterday:.2f}{eur_yesterday_str}"
        )
        send_telegram(message, bot_token, chat_ids)
        print(f"{name} Alarm gesendet!")
    else:
        print(f"Kein {name}-Alarm nötig.")


def send_test_message(bot_token, chat_ids):
    lines = ["Test erfolgreich!\n"]
    for name, usd_ticker, eur_ticker, threshold_pct in METALS:
        usd_yesterday, usd_now, change_pct, _, eur_now = get_price_change(usd_ticker, eur_ticker)
        if usd_yesterday is None:
            lines.append(f"{name}: Keine Daten verfügbar")
        else:
            eur_now_str = f" / €{eur_now:.2f}" if eur_now else ""
            print(f"{name} aktuell: ${usd_now:.2f}{eur_now_str}")
            print(f"Veränderung:     {change_pct:+.2f}%")
            lines.append(f"{name}: ${usd_now:.2f}{eur_now_str} ({change_pct:+.2f}% seit gestern, Alarm ab -{threshold_pct}%)")
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
        for name, usd_ticker, eur_ticker, threshold_pct in METALS:
            check_metal(name, usd_ticker, eur_ticker, threshold_pct, bot_token, chat_ids)


if __name__ == "__main__":
    main()
