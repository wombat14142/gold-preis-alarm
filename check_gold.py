import os
import json
import yfinance as yf
import requests
from datetime import date

METALS = [
    ("Gold",   "GC=F", 1.0),
    ("Silber", "SI=F", 2.5),
]

EUR_USD_TICKER = "EURUSD=X"
STATE_FILE = "alert_state.json"


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fetch_last_two(symbol):
    hist = yf.Ticker(symbol).history(period="5d", interval="1d")
    prices = hist["Close"].dropna()
    if len(prices) < 2:
        return None, None
    return float(prices.iloc[-2]), float(prices.iloc[-1])


def get_price_change(usd_ticker):
    usd_yesterday, usd_now = fetch_last_two(usd_ticker)
    if usd_yesterday is None:
        return None, None, None, None, None

    eurusd_yesterday, eurusd_now = fetch_last_two(EUR_USD_TICKER)
    change_pct = (usd_now - usd_yesterday) / usd_yesterday * 100
    eur_now = usd_now / eurusd_now if eurusd_now else None
    eur_yesterday = usd_yesterday / eurusd_yesterday if eurusd_yesterday else None

    return usd_yesterday, usd_now, change_pct, eur_yesterday, eur_now


def send_telegram(message, bot_token, chat_ids):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chat_id in chat_ids:
        response = requests.post(url, json={"chat_id": chat_id, "text": message})
        if not response.ok:
            print(f"Telegram Fehler für {chat_id}: {response.status_code} – {response.text}")


def send_error(message, bot_token, first_chat_id):
    print(f"FEHLER: {message}")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": first_chat_id, "text": f"⚠️ Fehler im Gold-Alarm:\n{message}"})
    except Exception as e:
        print(f"Fehler beim Senden der Fehlermeldung: {e}")


def check_metal(name, usd_ticker, threshold_pct, bot_token, chat_ids, state):
    try:
        usd_yesterday, usd_now, change_pct, eur_yesterday, eur_now = get_price_change(usd_ticker)
    except Exception as e:
        send_error(f"{name}: Datenabruf fehlgeschlagen ({usd_ticker}): {e}", bot_token, chat_ids[0])
        return

    if usd_yesterday is None:
        send_error(f"{name}: Nicht genug Daten von {usd_ticker}.", bot_token, chat_ids[0])
        return

    eur_now_str = f" / €{eur_now:.2f}" if eur_now else ""
    eur_yesterday_str = f" / €{eur_yesterday:.2f}" if eur_yesterday else ""

    print(f"{name} gestern:  ${usd_yesterday:.2f}{eur_yesterday_str}")
    print(f"{name} aktuell: ${usd_now:.2f}{eur_now_str}")
    print(f"Veränderung:     {change_pct:+.2f}%")

    if change_pct <= -threshold_pct:
        today = str(date.today())
        if state.get(name) == today:
            print(f"{name}: Heute bereits gewarnt, kein erneuter Alarm.")
            return
        message = (
            f"{name} Alarm!\n\n"
            f"Der {name}preis ist seit gestern um {change_pct:.1f}% gefallen.\n\n"
            f"Aktuell:  ${usd_now:.2f}{eur_now_str}\n"
            f"Gestern: ${usd_yesterday:.2f}{eur_yesterday_str}"
        )
        send_telegram(message, bot_token, chat_ids)
        state[name] = today
        print(f"{name} Alarm gesendet!")
    else:
        print(f"Kein {name}-Alarm nötig.")


def send_test_message(bot_token, chat_ids):
    lines = ["Test erfolgreich!\n"]
    for name, usd_ticker, threshold_pct in METALS:
        try:
            usd_yesterday, usd_now, change_pct, _, eur_now = get_price_change(usd_ticker)
            if usd_yesterday is None:
                lines.append(f"{name}: Keine Daten verfügbar ({usd_ticker})")
            else:
                eur_now_str = f" / €{eur_now:.2f}" if eur_now else ""
                print(f"{name} aktuell: ${usd_now:.2f}{eur_now_str}")
                print(f"Veränderung:     {change_pct:+.2f}%")
                lines.append(f"{name}: ${usd_now:.2f}{eur_now_str} ({change_pct:+.2f}% seit gestern, Alarm ab -{threshold_pct}%)")
        except Exception as e:
            lines.append(f"{name}: Fehler – {e}")
    send_telegram("\n".join(lines), bot_token, chat_ids)
    print("Testnachricht gesendet!")


def main():
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_ids = [os.environ["TELEGRAM_CHAT_ID"]]

    chat_id_2 = os.environ.get("TELEGRAM_CHAT_ID_2", "").strip()
    if chat_id_2:
        chat_ids.append(chat_id_2)

    try:
        if os.environ.get("FORCE_TEST", "").lower() == "true":
            send_test_message(bot_token, chat_ids)
        else:
            state = load_state()
            for name, usd_ticker, threshold_pct in METALS:
                check_metal(name, usd_ticker, threshold_pct, bot_token, chat_ids, state)
            save_state(state)
    except Exception as e:
        send_error(f"Unerwarteter Fehler: {e}", bot_token, chat_ids[0])
        raise


if __name__ == "__main__":
    main()
