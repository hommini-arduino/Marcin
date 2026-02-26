# Wyświetlacz centralki – ESP8266 + OLED (SSD1306 0.96" I2C)

Ten folder zawiera kod dla ESP8266 działającego jako **wyświetlacz centralki**.

## Wymagania
- ESP8266 (NodeMCU / Wemos D1 mini)
- OLED 0.96" SSD1306 128x64 I2C (adres zwykle 0x3C)
- Biblioteki Arduino:
  - Adafruit_GFX
  - Adafruit_SSD1306
  - ArduinoJson
  - ESP8266WiFi
  - ESP8266HTTPClient

## Połączenia OLED (I2C)
W kodzie użyto:
- `Wire.begin(14, 12)`
  - SDA = GPIO14 (D5)
  - SCL = GPIO12 (D6)

Jeśli używasz standardowych pinów NodeMCU:
- SDA = D2 (GPIO4)
- SCL = D1 (GPIO5)

to zmień na `Wire.begin(4, 5)`.

## Konfiguracja
W pliku `.ino` ustaw:
- `ssid`, `password`
- `rpi_ip`, `rpi_port`

## Endpointy API centralki
Kod zakłada:
- `GET /api/data` → JSON z polami `temperature`, `humidity`, `time`
- `GET /api/test` (opcjonalnie do testów)

## Pliki
- `wyswietlacz-ESP8266.ino` – główny program wyświetlacza
