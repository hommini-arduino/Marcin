# Zegar RTC z WiFi (Arduino + ESP8266 + Raspberry Pi)

## 📋 Opis
System zegara czasu rzeczywistego (RTC) z alarmami, wyświetlaczem LCD i komunikacją WiFi do centralki Raspberry Pi.

## 🔧 Komponenty
- **Arduino UNO R4 WiFi** - główny kontroler
- **DS3231 RTC** - moduł czasu rzeczywistego z alarmami
- **LCD I2C 20x4** - wyświetlacz
- **ESP8266** (NodeMCU / Wemos D1 Mini) - mostek WiFi
- **4x przyciski** - sterowanie
- **Buzzer** - alarm dźwiękowy
- **Raspberry Pi 4B** - centralka HTTP

## 🔌 Połączenia

### Arduino UNO R4 WiFi
```
DS3231 RTC:
  SDA -> A4
  SCL -> A5
  VCC -> 5V
  GND -> GND

LCD I2C (0x27):
  SDA -> A4
  SCL -> A5
  VCC -> 5V
  GND -> GND

ESP8266 (UWAGA: 3.3V!):
  SDA -> A4 (przez konwerter poziomów lub rezystor 4.7kΩ do 3.3V)
  SCL -> A5 (przez konwerter poziomów lub rezystor 4.7kΩ do 3.3V)
  GND -> GND
  VCC -> 3.3V (NIGDY 5V!)

Przyciski:
  Button1 (ustawianie czasu) -> pin 3 -> GND
  Button2 (zmiana wartości)  -> pin 4 -> GND
  Button3 (ustawianie alarmu) -> pin 5 -> GND
  Button4 (podświetlenie LCD) -> pin 6 -> GND

Buzzer:
  + -> pin 7
  - -> GND

Interrupt (alarm):
  DS3231 SQW -> pin 2
```

### ESP8266
```
NodeMCU / Wemos D1 Mini:
  D1 (GPIO5)  -> SCL (Arduino A5 przez konwerter)
  D2 (GPIO4)  -> SDA (Arduino A4 przez konwerter)
  GND         -> GND
  3.3V        -> zasilanie
```

**⚠️ WAŻNE:** ESP8266 działa na 3.3V! Użyj konwertera poziomów logicznych lub rezystorów pull-up 4.7kΩ do 3.3V.

## 🚀 Instalacja

### 1. Arduino IDE
1. Zainstaluj biblioteki:
   - `LiquidCrystal_I2C`
   - `Wire` (wbudowana)

2. Wgraj `sketch_sep22b.ino` na Arduino UNO R4 WiFi

3. **PRZED WGRANIEM** - skonfiguruj WiFi w funkcji sendWiFiConfig():
   ```cpp
   const char* config = "NazwaWiFi:HasloWiFi:192.168.1.100";
   //                    ^SSID      ^Password  ^IP Raspberry Pi
   ```

### 2. ESP8266
1. Zainstaluj w Arduino IDE:
   - Board: ESP8266 (https://arduino.esp8266.com/stable/package_esp8266com_index.json)
   - Biblioteki: `ESP8266WiFi`, `ESP8266HTTPClient`

2. Wybierz board: **NodeMCU 1.0** lub **LOLIN(Wemos) D1 mini**

3. Wgraj `ESP8266_WiFi_Bridge/ESP8266_WiFi_Bridge.ino`

### 3. Raspberry Pi
1. Zainstaluj Python 3 i Flask:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip
   pip3 install flask
   ```

2. Skopiuj `rpi_centralka.py` na RPi

3. Uruchom:
   ```bash
   python3 rpi_centralka.py
   ```

4. Otwórz przeglądarkę:
   ```
   http://[IP_RASPBERRY_PI]:5000/
   http://[IP_RASPBERRY_PI]:5000/kiosk
   ```

## 📡 Komunikacja

### Arduino → ESP8266 (I2C, co 3s)
- Czas (HH:MM:SS)
- Data (DD/MM/YY)
- Dzień tygodnia
- Temperatura
- Alarmy (2x: czas + status ON/OFF)
- Status alarmu (czy dzwoni)

### ESP8266 → Raspberry Pi (HTTP POST)
- Endpoint: `http://[RPi_IP]:5000/api/clock/data`
- Format: JSON
- Interwał: 3 sekundy

### Raspberry Pi → ESP8266 → Arduino
Komendy w odpowiedzi HTTP:
- **Sync czasu z NTP**: `/api/clock/sync_time` (POST)
- **Ustawianie alarmu**: `/api/clock/set_alarm` (POST)
- **Wyłączanie alarmu**: `/api/clock/stop_alarm` (POST)

## 🎛️ API Raspberry Pi

### `GET /api/clock/status`
Zwraca aktualny status zegara:
```json
{
  "time": "14:30:45",
  "date": "06/02/2026",
  "temperature": 23,
  "alarm1": {"time": "07:00", "enabled": true},
  "alarm2": {"time": "12:30", "enabled": false},
  "alarming": false
}
```

### `POST /api/clock/sync_time`
Synchronizuje czas z serwerem (NTP):
```bash
curl -X POST http://192.168.1.100:5000/api/clock/sync_time
```

### `POST /api/clock/set_alarm`
Ustawia alarm:
```bash
curl -X POST http://192.168.1.100:5000/api/clock/set_alarm \
  -H "Content-Type: application/json" \
  -d '{"alarm":1, "hour":7, "minute":30, "enabled":true}'
```

### `POST /api/clock/stop_alarm`
Wyłącza dzwoniący alarm:
```bash
curl -X POST http://192.168.1.100:5000/api/clock/stop_alarm
```

## 🐛 Troubleshooting

### ESP8266 nie łączy się z WiFi
1. Sprawdź SSID i hasło w Arduino
2. Sprawdź monitor szeregowy ESP8266 (115200 baud)
3. Upewnij się że router WiFi działa na 2.4GHz (ESP8266 nie obsługuje 5GHz)

### Arduino nie komunikuje się z ESP8266
1. Sprawdź połączenia I2C (SDA/SCL)
2. Użyj skanera I2C aby sprawdzić adres 0x08
3. Upewnij się że używasz konwertera poziomów 5V↔3.3V

### Raspberry Pi nie otrzymuje danych
1. Sprawdź IP RPi: `hostname -I`
2. Sprawdź czy Flask działa: `curl http://localhost:5000/api/test`
3. Sprawdź logi ESP8266 w monitorze szeregowym
4. Sprawdź firewall na RPi

### LCD pokazuje śmieci
1. Sprawdź adres I2C LCD (0x27 lub 0x3F)
2. Użyj skanera I2C
3. Sprawdź kontrast potencjometrem na LCD

## 📊 Struktura danych I2C

### Arduino → ESP8266 (komenda 'D'):
```c
struct ClockData {
  uint8_t hour;           // 0-23
  uint8_t minute;         // 0-59
  uint8_t second;         // 0-59
  uint8_t day;            // 1-7 (1=Niedziela)
  uint8_t date;           // 1-31
  uint8_t month;          // 1-12
  uint8_t year;           // 0-99 (20xx)
  int8_t temperature;     // -128 do 127 °C
  uint8_t alarm1_hour;    // 0-23
  uint8_t alarm1_minute;  // 0-59
  bool alarm1_status;     // true/false
  uint8_t alarm2_hour;    // 0-23
  uint8_t alarm2_minute;  // 0-59
  bool alarm2_status;     // true/false
  bool alarming;          // true jeśli alarm dzwoni
};
```

### ESP8266 → Arduino (komendy):
- **'T'** - Sync czasu: `[h,m,s,day,date,month,year]` (7 bajtów)
- **'A'** - Ustaw alarm: `[num,h,m,enabled]` (4 bajty)
- **'S'** - Stop alarm: brak danych

## 📝 Licencja
MIT

## 👤 Autor
Marcin Zieliński - Wersja 1.2 + WiFi Extension