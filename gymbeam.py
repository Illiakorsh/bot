import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta


# === Налаштування Telegram ===
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# === Налаштування сайту GymBeam ===
LOGIN_URL = ""
SHIFTS_URL = ""
EMAIL = ""
PASSWORD = ""

# === Файл для збереження змін ===
DATA_FILE = "shifts.json"
LAST_CHANGE_FILE = "last_change.json"


# === Функція для запуску браузера ===
def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Запуск без GUI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# === Функція для авторизації ===
def login(driver):
    driver.get(LOGIN_URL)
    time.sleep(3)  # Чекаємо, поки завантажиться сторінка

    # Вводимо email
    email_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "login"))
    )
    email_input.send_keys(EMAIL)

    # Вводимо пароль
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)

    time.sleep(5)  # Чекаємо завершення авторизації

# === Функція для отримання змін ===
def get_shifts(driver):
    driver.get(SHIFTS_URL)
    time.sleep(3)

    shifts = []
    articles = driver.find_elements(By.TAG_NAME, "article")

    for article in articles:
        title_element = article.find_element(By.TAG_NAME, "h2")
        link_element = article.find_element(By.TAG_NAME, "a")

        title = title_element.text.strip() if title_element else "Без заголовка"
        link = link_element.get_attribute("href") if link_element else SHIFTS_URL

        shifts.append({"title": title, "link": link})

    return shifts

# === Функція для читання старих змін ===
def load_old_shifts():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# === Функція для збереження змін ===
def save_shifts(shifts):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(shifts, file, ensure_ascii=False, indent=4)

# === Функція для надсилання повідомлень у Telegram ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}

    response = requests.post(url, json=data)

    if response.status_code == 200:
        print(f"✅ Повідомлення надіслано: {message}")
    else:
        print(f"❌ Помилка надсилання: {response.status_code}, {response.text}")
# === 6 годин перевірки змін ===
def load_last_change_time():
    try:
        with open(LAST_CHANGE_FILE, "r") as file:
            timestamp = json.load(file).get("last_change")
            return datetime.fromisoformat(timestamp)
    except Exception:
        return None

def save_last_change_time():
    with open(LAST_CHANGE_FILE, "w") as file:
        json.dump({"last_change": datetime.now().isoformat()}, file)


# === Основна функція перевірки змін ===
def check_for_new_shifts():
    driver = init_browser()
    
    try:
        login(driver)  # Авторизація

        new_shifts = get_shifts(driver)
        old_shifts = load_old_shifts()

        print(f"🆕 Нові зміни: {new_shifts}")
        print(f"📜 Старі зміни: {old_shifts}")

        # Знайти нові зміни
        added_shifts = [shift for shift in new_shifts if shift not in old_shifts]

        if added_shifts:
            send_telegram_message(f"🔍 Нові зміни знайдено: {len(added_shifts)}")
            for shift in added_shifts:
                message = f"🔔 Нова зміна: {shift['title']}\nДеталі: {shift['link']}"
                send_telegram_message(message)

            # Оновити файл тільки якщо є нові зміни
            save_shifts(new_shifts)
            save_last_change_time() 
        else:
            print("✅ Нових змін немає.")
            last_change = load_last_change_time()
            if last_change:
                hours_passed = (datetime.now() - last_change).total_seconds() / 1800
                if hours_passed >= 6:
                    send_telegram_message("ℹ️ Нових змін не було вже понад 6 годин.")
                    # Оновлюємо час, щоб не спамити кожні 10 хвилин
                    save_last_change_time()
            else:
                save_last_change_time()
    
    finally:
        driver.quit()  # Закриваємо браузер у будь-якому випадку

# === Запускаємо перевірку кожні 10 хвилин ===
if __name__ == "__main__":
    while True:
        check_for_new_shifts()
        time.sleep(600)  # Чекаємо 10 хвилин перед наступною перевіркою
