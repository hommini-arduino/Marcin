#include <Wire.h>  

void setup() {  
  Wire.begin(4, 5); // Join I2C bus with SDA on GPIO 4 and SCL on GPIO 5  
  Serial.begin(115200);  
  Serial.println("I2C Communication with ESP8266");  
}  

void loop() {  
  Wire.requestFrom(8, 6); // Request 6 bytes from slave device with address 8  
  while (Wire.available()) {  
    char c = Wire.read(); // Receive a byte as character  
    Serial.print(c); // Print the character  
  }  
  delay(1000); // Wait for a second  
}