#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import socket
import fcntl
import struct
import warnings
from time import gmtime, strftime
from modules import app, cbpi
from .contextmanagers import cursor, cleared
from .gpio import CharLCD as GpioCharLCD
from i2c import CharLCD


def set_lcd_adress():

  ref = cbpi.get_config_parameter('LCD_Adress', None)
  if ref is None:
      cbpi.add_config_parameter("LCD_Adress", "0x27", "string", "Adress of the LCD, CBPi reboot required")
      ref = cbpi.get_config_parameter('LCD_Adress', None)
  if len(ref) != 4:
      #cbpi.notify("LCD Adress is wrong", "Change LCD Adress in parameters", timeout=None)
      pass #exeption definieren 
  return ref
LCDadress = int(set_lcd_adress(),16)
cbpi.app.logger.info("LCDDisplay  - LCD_Adress %s %s" % (set_lcd_adress(),LCDadress))

#adress should be somthing like 0x27, 0x37 etc.
#comand promt in Raspi: sudo i2cdetect -y 1 or sudo i2cdetect -y 0 to see the adress
lcd = CharLCD(i2c_expander='PCF8574', address=LCDadress, port=1,
              cols=20, rows=4, dotsize=8,
              charmap='A00',
              auto_linebreaks=True,
              backlight_enabled=True)


def set_parameter_refresh():

  ref = cbpi.get_config_parameter('LCD_Refresh', None)
  if ref is None:
      cbpi.add_config_parameter("LCD_Refresh", 5, "number", "Time to remain till next display in sec, CBPi reboot required")
      ref = cbpi.get_config_parameter('LCD_Refresh', None)
  return ref

refresh = float(set_parameter_refresh())
cbpi.app.logger.info("LCDDisplay  - Refeshrate %s" % (refresh))

def set_parameter_multidisplay():
  
  multi = cbpi.get_config_parameter('LCD_Multidisplay', None)
  if multi is None:
      cbpi.add_config_parameter("LCD_Multidisplay", "on", "select", "Toggle between all Kettles or show only one Kette constantly, CBPi reboot required", ["on","off"])

      multi=cbpi.get_config_parameter('LCD_Multidisplay', None)
  return multi

multidisplay = str(set_parameter_multidisplay())
cbpi.app.logger.info("LCDDisplay  - Multidisplay %s" % (multidisplay))

def set_parameter_id1():
  
  kid1 = cbpi.get_config_parameter("LCD_Singledisplay", None)
  if kid1 is None:
      cbpi.add_config_parameter("LCD_Singledisplay", 1, "number", "Choose Kettle (Number), CBPi reboot required")
      kid1 = cbpi.get_config_parameter('LCD_Singledisplay', None)
  return kid1

id1 = int(set_parameter_id1())
cbpi.app.logger.info("LCDDisplay  - Kettlenumber used %s" % (id1))

def get_ip(interface):
    ip_addr = "Not connected"
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        ip_addr = socket.inet_ntoa(fcntl.ioctl(so.fileno(), 0x8915, struct.pack('256s', interface[:15]))[20:24])
    finally:
        return ip_addr

def get_version_fo(path):
    version = ""
    try:
        if path is not "":
            fo = open(path, "r")
        else:
            fo = open("/home/pi/craftbeerpi3/config/version.yaml","r")
        version = fo.read();
        fo.close()
    finally:
        return version
version = (get_version_fo(""))

bierkrug = (
              0b00000,
	      0b00000,
	      0b11100,
	      0b11100,
	      0b11111,
	      0b11101,
	      0b11111,
	      0b11100
        )
lcd.create_char(0, bierkrug)
global bk #variable for on off of the beerglassymbol (BierKrug) doesnot know better than use semioptimal global var.
bk = 0

##Background Task to load the data
@cbpi.backgroundtask(key="lcdjob", interval=0.7)
def lcdjob(api):
    ## YOUR CODE GOES HERE

    s = cbpi.cache.get("active_step")

    if get_ip('wlan0') == "Not connected":
        ip = get_ip('eth0')
    else:
        ip = get_ip('wlan0')

    if s is not None:

        if multidisplay == "on":
            lcd.clear()
            for idx, value in cbpi.cache["kettle"].iteritems():
                current_sensor_value = float(cbpi.get_sensor_value(value.sensor))

                line1 = (u'%s' % (s.name,))[:20]

                #line2 when steptimer is runnig show remaining time instead of kettlename
                if s.timer_end is not None:
                    time_remaining = time.strftime(u"%H:%M:%S", time.gmtime(s.timer_end - time.time()))
                    line2 = ((u"%s %s" % ((value.name).ljust(12)[:11], time_remaining)).ljust(20)[:20])
                else:
                    line2 = ((u'%s' % (value.name,))[:20])

                line3 = (u"Targ. Temp:%6.2f%s" % (float(value.target_temp),(u"°C")))[:20]
                line4 = (u"Curr. Temp:%6.2f%s" % ((current_sensor_value),(u"°C")))[:20]

                lcd.cursor_pos = (0, 0)
                lcd.write_string(line1)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(line2)
                lcd.cursor_pos = (2, 0)
                lcd.write_string(line3)
                lcd.cursor_pos = (3, 0)
                lcd.write_string(line4)

                time.sleep(refresh)

                pass
        else:
            #lcd.clear()
            #singlemode
            current_sensor_value_id1 = float(cbpi.get_sensor_value(id1))

            line1 = (u'%s' % (s.name,)).ljust(20)[:20]

            #line2 when steptimer is runnig show remaining time instead of kettlename
            if s.timer_end is not None:
                time_remaining = time.strftime(u"%H:%M:%S", time.gmtime(s.timer_end - time.time()))
                line2 = ((u"%s %s" % ((cbpi.cache.get("kettle")[id1].name).ljust(12)[:11],time_remaining)).ljust(20)[:20])
            else:
                line2 = ((u'%s' % (cbpi.cache.get("kettle")[id1].name)).ljust(20)[:20])
                
            line3 = (u"Targ. Temp:%6.2f%s" % (float(cbpi.cache.get("kettle")[id1].target_temp),(u"°C"))).ljust(20)[:20]
            line4 = (u"Curr. Temp:%6.2f%s" % ((current_sensor_value_id1),(u"°C"))).ljust(20)[:20]


            lcd.cursor_pos = (0, 0)
            lcd.write_string(line1)
            lcd.cursor_pos = (0,19)
            if bk == 0 and s.timer_end is None:        
                lcd.write_string(u"\x00")
                global bk
                bk = 1
            else:
                lcd.write_string(u" ")
                global bk
                bk = 0
            lcd.cursor_pos = (1, 0)
            lcd.write_string(line2)
            lcd.cursor_pos = (2, 0)
            lcd.write_string(line3)
            lcd.cursor_pos = (3, 0)
            lcd.write_string(line4)

    else:
        lcd.cursor_pos = (0, 0)
        lcd.write_string((u"CraftBeerPi %s" % version).ljust(20))
        lcd.cursor_pos = (1, 0)
        lcd.write_string((u'%s' % (cbpi.get_config_parameter('brewery_name','No Brewery'))).ljust(20)[:20])
        lcd.cursor_pos =(2, 0)
        lcd.write_string((u"IP: %s" % ip).ljust(20)[:20])
        lcd.cursor_pos = (3, 0)
        lcd.write_string((strftime(u"%Y-%m-%d %H:%M:%S", time.localtime())).ljust(20))
    pass
