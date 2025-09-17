import logging
import time

from PIL import Image, ImageDraw, ImageFont

from bin.SSD1306 import SSD1306_128_64
from bin.Utils import Utils, HassioUtils

class Display:
    DEFAULT_BUSNUM = 1
    SCREENSHOT_PATH = "./img/examples/"

    def __init__(self, busnum = None, screenshot = False, config = None):
        self.logger = logging.getLogger('Display')

        if not isinstance(busnum, int):
            busnum = Display.DEFAULT_BUSNUM
        self.display = SSD1306_128_64(busnum)
        self.clear()
        self.width = self.display.width
        self.height = self.display.height

        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.screenshot = screenshot

    def clear(self):
        self.display.begin()
        self.display.clear()
        self.display.display()

    def prepare(self):
        self.draw.rectangle((0, 0, self.width, self.height), outline = 0, fill = 0)

    def show(self):
        self.display.image(self.image)
        self.display.display()

    def capture_screenshot(self, name):
        if self.screenshot:
            if isinstance(self.screenshot, str):
                dir = self.screenshot
            else:
                dir = Display.SCREENSHOT_PATH

            path = dir.rstrip('/') + '/' + name.lower() + '.png'
            self.logger.info("saving screenshot to '" + path + "'")
            self.image.save(path)

class BaseScreen:
    font_path = Utils.current_dir + "/fonts/PixelOperator.ttf"
    font_bold_path = Utils.current_dir + "/fonts/DejaVuSans-Bold.ttf"
    font_icon = Utils.current_dir + "/fonts/lineawesome-webfont.ttf"
    fonts = {}

    def __init__(self, duration, display = Display(), utils = Utils(), config = None):
        self.display = display
        self.duration = duration
        self.utils = utils
        self.config = config
        self.font_size = 8
        self.logger = logging.getLogger('Screen')
        self.logger.info("'" + self.__class__.__name__ + "' created")

    @property
    def name(self):
        return str(self.__class__.__name__).lower().replace("screen", "")

    @property
    def text_indent(self):
        """ :return: how far to indent a line of text for this screen """
        return 0

    def capture_screenshot(self, name = None):
        if not name:
            name = self.name
        self.display.capture_screenshot(name)

    def display_text(self, text_lines):
        """ Display multiple lines of text with auto-resizing/positioning
            of the text based on the passed in text. """
        if not text_lines:
           return

        # set the number of lines, which reconfigures fonts
        self.set_text_lines(len(text_lines))
        font = self.font()

        line = 0
        for text in text_lines:
           # display the text line at the correct x / y based on config
           x = self.text_indent
           y = self.text_y[line]
           self.display.draw.text((x, y), text, font=font, fill=255)

           line += 1
           if line >= 3:
              return # too many lines passed in!

    def set_text_lines(self, num_lines):
       """ Set the number of text lines that will be displayed. """
       self.text_lines = num_lines

       # set defaults based on number of lines
       if self.text_lines > 2:
          self.font_size = 10
       else:
          self.font_size = 14

    @property
    def text_y(self):
        if self.text_lines == 1:
           return [0]
        elif self.text_lines == 2:
           return [0, 18]
        elif self.text_lines == 3:
           return [0, 11, 21]
        else:
           return None

    def font(self, size = None, is_bold = False, is_icon = False):
        # default to the current screen's font size if none provided
        if not size:
           size = self.font_size

        suffix = None
        if is_bold:
            suffix = '_bold'
        elif is_icon:
            suffix = '_icon'

        key = 'font_{}{}'.format(str(size), suffix)

        if key not in BaseScreen.fonts:
            font = BaseScreen.font_path
            if is_bold:
                font = BaseScreen.font_bold_path
            elif is_icon:
                font = BaseScreen.font_icon

            font = ImageFont.truetype(font, int(size))
            BaseScreen.fonts[key] = font
        return BaseScreen.fonts[key]

    @property
    def default_message(self):
        return 'Welcome to ' + self.utils.get_hostname()

    def render(self):
        self.display.show()

    def run(self):
        self.logger.info("'" + self.__class__.__name__ + "' rendering")
        self.display.prepare()
        self.render()
        self.logger.info("'" + self.__class__.__name__ + "' completed")

class NetworkScreen(BaseScreen):
    def render(self):
        hostname = self.utils.get_hostname()
        ipv4 = self.utils.get_ip()

        # Draw Icons
        self.display.draw.text((0, 3), chr(int("0xf796", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # ethernet
        self.display.draw.text((0, 23), chr(int("0xf233", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # server
        self.display.draw.text((0, 43), chr(int("0xf1eb", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # wifi
        # Draw Text
        self.display.draw.text((19, 3), "Network", font=self.font(16), fill=255)
        self.display.draw.text((19, 23), hostname, font=self.font(16), fill=255)
        self.display.draw.text((19, 43), ipv4, font=self.font(16), fill=255)

        self.display.show()
        time.sleep(self.duration)

class StorageScreen(BaseScreen):
    def render(self):
        drive = '/'
        storage = Utils.shell_cmd('df ' + drive + ' | awk \'$NF=="/"{printf "%.0f,%.0f,%.0f", $3/(1024*1024), $2/(1024*1024), 100*($2-$3)/$2 }\'')
        storage = storage.split(',')
        used = int(storage[0])
        total = int(storage[1])
        free_pct = float(storage[2])

        # Draw Icons
        self.display.draw.text((0, 3), chr(int("0xf538", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # memory
        # Draw Text
        self.display.draw.text((19, 3), "Storage", font=self.font(16), fill=255)
        self.display.draw.text((0, 23), "Used: " + str(used) + "/" + str(total) + "GB", font=self.font(16), fill=255)
        self.display.draw.text((0, 43), "Free: " + str(free_pct) + "%", font=self.font(16), fill=255)

        self.display.show()
        time.sleep(self.duration)

class MemoryScreen(BaseScreen):
    def render(self):
        mem = Utils.shell_cmd("free -m | awk 'NR==2{printf \"%.0f,%.0f,%.0f\", $3/1024, $2/1024, 100*($2-$3)/$2 }'")
        mem = mem.split(',')
        used = int(mem[0])
        total = int(mem[1])
        free_pct = float(mem[2])

        # Draw Icons
        self.display.draw.text((0, 3), chr(int("0xf538", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # memory
        # Draw Text
        self.display.draw.text((19, 3), "Memory", font=self.font(16), fill=255)
        self.display.draw.text((0, 23), "Used: " + str(used) + "/" + str(total) + "GB", font=self.font(16), fill=255)
        self.display.draw.text((0, 43), "Free: " + str(free_pct) + "%", font=self.font(16), fill=255)

        self.display.show()
        time.sleep(self.duration)

class CpuScreen(BaseScreen):
    def set_temp_unit(self, unit):
        unit = str(unit).upper()
        if unit in ['C', 'F']:
            self.temp_unit = unit

    def get_temp(self):
        temp = float(Utils.shell_cmd("cat /sys/class/thermal/thermal_zone0/temp")) / 1000.00
        if (hasattr(self, 'temp_unit') and self.temp_unit == 'F'):
            temp = "%0.1f °F" % (temp * 9.0 / 5.0 + 32)
        else:
            temp = "%0.1f °C" % (temp)
        return temp

    def render(self):
        temp = self.get_temp()
        core_stats = HassioUtils().hassos_get_info('core/stats', self.config)	
        cpu = core_stats["data"]['cpu_percent']
        uptime = Utils.shell_cmd("uptime | grep -ohe 'up .*' | sed 's/,//g' | awk '{ print $2" "$3 }'")

        # Draw Icons
        self.display.draw.text((0, 3), chr(int("0xf2db", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # microchip
        self.display.draw.text((0, 23), chr(int("0xf2c9", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # thermometer-half
        self.display.draw.text((65, 23), chr(int("0xf3fd", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # tachometer-alt
        self.display.draw.text((0, 43), chr(int("0xf2f2", 0)), font=self.font(18, is_bold=False, is_icon=True), fill=255) # stopwatch
        # Draw Text
        self.display.draw.text((19, 3), "CPU", font=self.font(16), fill=255)
        self.display.draw.text((19, 23), str(temp), font=self.font(16), fill=255)
        self.display.draw.text((87, 23), str(cpu), font=self.font(16), fill=255)
        self.display.draw.text((19, 43), uptime, font=self.font(16), fill=255)

        self.display.show()
        time.sleep(self.duration)
