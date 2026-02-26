# CENTRALKA (Raspberry Pi / Flask) + ESP8266 + OLED 0.96" (SSD1306 I2C)

Projekt „Centralki” do zbierania danych (temperatura/wilgotność) z wielu urządzeń po **TCP** i udostępniania ich przez **API HTTP (Flask)** oraz wyświetlania na **OLED (ESP8266)**.

## Co to robi?

- **Serwer TCP (RPi/PC):** odbiera dane z wielu urządzeń (ESP8266 / Arduino UNO R4 WiFi / inne) na jednym porcie.
- **API HTTP (Flask):**
  - `/api/devices` – lista urządzeń + ostatnie dane,
  - `/api/data` – kompatybilność: „ostatni dowolny odczyt” (z dowolnego urządzenia),
  - `/api/test` – test działania serwera.
- **Wyświetlacz OLED (ESP8266):** pobiera dane z API i wyświetla je na ekranie SSD1306 128×64.

---

## Wymagania

### Serwer (Raspberry Pi / Linux / PC)
- Python 3.9+ (zwykle wystarczy 3.10+)
- Flask

### ESP8266 + OLED
- ESP8266 (NodeMCU / Wemos D1 Mini)
- OLED 0.96" SSD1306 128×64 **I2C** (najczęściej adres `0x3C`)
- Biblioteki Arduino:
  - `ESP8266WiFi`
  - `ESP8266HTTPClient`
  - `Adafruit GFX Library`
  - `Adafruit SSD1306`
  - `ArduinoJson`

---

## Okablowanie (ESP8266 + OLED I2C)

### Wersja z pinami jak na schemacie (GPIO14/GPIO12)
To pasuje do ustawienia:
- `Wire.begin(14, 12); // SDA=GPIO14 (D5), SCL=GPIO12 (D6)`

Połączenia:
- **OLED SDA → GPIO14 / D5**
- **OLED SCL → GPIO12 / D6**
- **OLED VCC → 3.3V**
- **OLED GND → GND**

> Uwaga: Typowo w wielu przykładach NodeMCU/Wemos spotkasz też I2C jako SDA=D2(GPIO4), SCL=D1(GPIO5).
> W tym repo używasz wariantu SDA=D5(GPIO14), SCL=D6(GPIO12) — i to jest OK, jeśli tak masz podłączone.

---

## Uruchomienie serwera (Python/Flask)

1. Wejdź na RPi/PC do folderu z serwerem.
2. Zainstaluj zależności:
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install flask
   ```
   (Jeśli serwer używa dodatkowych bibliotek – doinstaluj według potrzeb.)

3. Uruchom serwer:
   ```bash
   python3 centralka_server.py
   ```

Po uruchomieniu zwykle zobaczysz w konsoli informację o:
- porcie WEB (np. `5000`),
- porcie TCP (np. `8080`),
- adresach URL do panelu i kiosku.

---

## Format danych wysyłanych po TCP (urządzenia → serwer)

Serwer (wariant multi-device) zwykle rozumie m.in.:

### 1) Format tekstowy
```text
DEV:esp1:TEMP:23.5:HUM:45
DEV:uno1:TEMP:24.1:HUM:44
```

### 2) Bez DEV (ID = IP nadawcy)
```text
TEMP:23.5:HUM:45
```

### 3) JSON
```json
{"dev":"esp1","temp":23.5,"hum":45}
```

---

## API (Flask)

### `GET /api/data`
Kompatybilnościowy endpoint: zwraca „ostatni dowolny” odczyt.

Przykładowa odpowiedź:
```json
{
  "temperature": "23.5",
  "humidity": "45",
  "time": "12:34:56",
  "source": "esp1"
}
```

### `GET /api/devices`
Zwraca mapę urządzeń (`dev_id -> dane`), np.:
```json
{
  "esp1": {
    "temperature": "23.5",
    "humidity": "45",
    "time": "12:34:56",
    "ip": "192.168.1.50"
  },
  "uno1": {
    "temperature": "24.1",
    "humidity": "44",
    "time": "12:34:52",
    "ip": "192.168.1.51"
  }
}
```

### `GET /api/test`
Szybki test:
```json
{
  "status": "ok",
  "time": "12:34:56",
  "message": "Serwer działa",
  "devices_count": 2
}
```

---

## ESP8266 + OLED: co ustawić w kodzie

W szkicu ESP8266 ustaw:
- `ssid`, `password`
- `rpi_ip` oraz `rpi_port` (port HTTP z Flask, zwykle `5000`)
- upewnij się, że I2C `Wire.begin(SDA, SCL)` pasuje do Twojego okablowania

Jeśli OLED nie działa:
- sprawdź adres I2C: najczęściej `0x3C`, czasem `0x3D`
- sprawdź zasilanie (OLED musi mieć 3.3V)
- sprawdź, czy nie pomyliłeś SDA/SCL

---

## Troubleshooting

### OLED: czarny ekran
- zły adres: spróbuj `0x3D` zamiast `0x3C`
- zły wiring SDA/SCL
- brak wspólnej masy (GND)

### ESP8266: nie pobiera danych
- sprawdź, czy `rpi_ip:rpi_port` jest osiągalne z WiFi
- wejdź w przeglądarce na:
  - `http://<IP_RPI>:5000/api/test`
  - `http://<IP_RPI>:5000/api/data`

### Serwer: nie widzi urządzeń po TCP
- upewnij się, że port TCP (np. `8080`) jest otwarty i urządzenia wysyłają na poprawny IP/port
- sprawdź logi serwera (czy widać połączenia i odebrane linie)

---

## Plan / pomysły rozwoju
- plik `requirements.txt`
- uruchomienie jako `systemd service` na Raspberry Pi
- dodatkowe endpointy: `/api/data/<dev_id>`
- obsługa ikon/alertów na OLED (np. stale data / offline)
