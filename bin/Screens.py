import logging
import textwrap
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps

from bin.Scroller import Scroller
from bin.SSD1306 import SSD1306_128_64, SSD1306_128_32
from bin.Utils import Utils, HassioUtils

class Display:
    DEFAULT_BUSNUM = 1
    SCREENSHOT_PATH = "./img/examples/"

    def __init__(self, busnum = None, screenshot = False, rotate = False, config = None, show_icons = True,
                 compact = False, show_hint = False, size = '32', icon_stats = 'text'):
        self.logger = logging.getLogger('Display')

        if not isinstance(busnum, int):
            busnum = Display.DEFAULT_BUSNUM
        if size == '64':
            self.display = SSD1306_128_64(busnum)
        else:
            self.display = SSD1306_128_32(busnum)
        self.clear()
        self.width = self.display.width
        self.height = self.display.height
        self.rotate = rotate

        self.compact = compact
        self.show_icons = show_icons
        self.show_hint = show_hint
        self.icon_stats = icon_stats
        self.hint_right = True

        if self.show_icons and self.show_hint:
           self.logger.error("show_icons and show_hint both True; turning off hint")
           self.show_hint = False

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
        if isinstance(self.rotate, int):
            self.image = self.image.rotate(self.rotate)
            self.draw = ImageDraw.Draw(self.image)

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
        self.hint = None
        self.icon = None
        self.font_size = 8
        self.logger = logging.getLogger('Screen')
        self.logger.info("'" + self.__class__.__name__ + "' created")

    @property
    def name(self):
        return str(self.__class__.__name__).lower().replace("screen", "")

    def set_icon(self, path):
        """ set the image for this screen """
        if not self.icon or self.icon_path != path:
           self.icon_path = path
           img = Image.open(r"" + Utils.current_dir + self.icon_path)
           # img = img.convert('RGBA') # MUST be in RGB mode for the OLED
           # invert black icon to white (255) for OLED display
           #self.icon = ImageOps.invert( self.icon )
           self.icon = img.resize([30, 30])

    @property
    def text_indent(self):
        """ :return: how far to indent a line of text for this screen """
        if self.display.show_icons and self.icon:
            return 29
        elif self.hint and not self.display.hint_right:
            return 16
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
          if self.text_indent < 10:
             self.font_size = 10
          else:
             self.font_size = 9
       else:
          if self.text_indent < 10:
             self.font_size = 14
          else:
             self.font_size = 13

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

    def display_hint(self):
       if not self.hint or not self.display.show_hint:
           return

       # determine whether to put hints on right or left
       x_pos = 0
       if self.display.hint_right:
          x_pos = 119
       font = self.font(size=11, is_bold=True)

       draw = self.display.draw
       draw.rectangle((x_pos, 0, x_pos + 10, 32), outline = 255, fill = 255)

       # display the text based on how many characters the hint is
       text_fill = 0
       draw.text((x_pos, -2), self.hint[0], font=font, fill=text_fill)
       if (len(self.hint) > 1):
           draw.text((x_pos, 8), self.hint[1], font=font, fill=text_fill)
       if (len(self.hint) > 2):
           draw.text((x_pos, 18), self.hint[2], font=font, fill=text_fill)

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

    # helper function to display the current page (used by standard screens)
    def render_with_defaults(self):
        self.display_hint()

        # add icon to canvas (if enabled)
        if self.display.show_icons and self.icon:
           self.display.image.paste(self.icon, (-3, 3))

        self.capture_screenshot()
        self.display.show()
        time.sleep(self.duration)

    def render(self):
        self.display.show()

    def render_scroller(self, text, font, amplitude = 0, startpos = None):
        if not startpos:
            startpos = self.display.width
        scroller = Scroller(text, startpos, font, self.display, amplitude)
        timer = time.time() + self.duration
        while self.config.allow_screen_render(self.name):
            self.display.prepare()
            scroller.render()
            self.display.show()

            if scroller.pos == 2:
                self.capture_screenshot()

            if not self.config.allow_screen_render(self.name) or not scroller.move_for_next_frame(time.time() < timer):
                break

    def run(self):
        self.logger.info("'" + self.__class__.__name__ + "' rendering")
        self.display.prepare()
        self.render()
        self.logger.info("'" + self.__class__.__name__ + "' completed")

class StaticScreen(BaseScreen):
    @property
    def text(self):
        if not self._text:
            self.text = self.default_message
            self.logger.info("No static text found")

        if not self._text_compiled:
            self._text_compiled = True
            self._text = self.utils.compile_text(self._text)
            self.logger.info(f"Static screen text compiled: '{self._text}'")

        return self._text

    @text.setter
    def text(self, text):
        self._text = str(text)
        self._text_compiled = False
        self.logger.info(f"Static screen text: '{self._text}' added")

    @property
    def noscroll(self):
        if not hasattr(self, '_noscroll'):
            return False
        return self._noscroll

    @noscroll.setter
    def noscroll(self, state):
        self._noscroll = bool(state)
        self.logger.info(f"Static screens text animated set to '{str(self._noscroll)}'")

    # @property
    # def amplitude(self):
    #     if not self._amplitude:
    #         return 0
    #     return self._amplitude

    # @amplitude.setter
    # def amplitude(self, amplitude):
    #     self._amplitude = int(amplitude) * -1
    #     self.logger.info("Static screen amplitude: '" + str(self._amplitude) + "' set")

    def capture_screenshot(self):
        slug = Utils.slugify(self.text)
        super().capture_screenshot("static_" + slug)

    def render(self):
        self.display.prepare()
        font = self.font(size=16)
        text = self.text
        # amplitude = self.amplitude

        self.logger.info("Rendering static text: " + text)
        if not self.noscroll and Utils.requires_scroller(self.display, text, font):
            self.render_scroller(text, font)
        else:
            if not Utils.does_text_width_fit(self.display, text, font):
                self.logger.info("Static text too wide for screen")
                lines = textwrap.wrap(text, width=15)
                font = self.font(12)
                text_leading = 3
                y_text = self.display.height
                for i, line in enumerate(lines):
                    width, height = Utils.get_text_size(self.display, line, font)
                    new_y = y_text - height - (text_leading / 2)
                    if new_y > 0:
                        y_text = new_y
                    else:
                        y_text = 0
                        break

                y_text /= 2
                for line in lines:
                    width, height = Utils.get_text_size(self.display, line, font)
                    left = (self.display.width - width) / 2
                    self.display.draw.text((left, y_text), line, font=font, fill=255)
                    y_text += (height + text_leading)
            else:
                x, y = Utils.get_text_center(self.display, text, font)
                self.display.draw.text((x, y), self.text, font=font, fill=255)

            self.render_with_defaults()

class WelcomeScreen(BaseScreen):
    @property
    def text(self):
        if not self._text:
            self.text = self.default_message
            self.logger.info("No configured welcome text found")

        if not self._text_compiled:
            self._text_compiled = True
            self._text = self.utils.compile_text(self._text)
            self.logger.info("Welcome screen text compiled: '" + self._text + "'")

        return self._text

    @text.setter
    def text(self, text):
        self._text = str(text)
        self._text_compiled = False
        self.logger.info("Welcome screen text: '" + self._text + "' added")

    def render(self):
        '''
        Animated welcome screen
        Scrolls 'Welcome [hostname]' across the screen
        '''
        height = self.display.height
        font = self.font(size=16)
        self.render_scroller(self.text, font)

class SplashScreen(BaseScreen):
    img = Image.open(r"" + Utils.current_dir + "/img/home-assistant-logo.png")

    def __init__(self, duration, display = Display(), utils = Utils(), config = None):
        super().__init__(duration, display, utils, config)

    def render(self):
        '''
            Home Assistant screen. 
            If you're not using Home Assistant OS, disable this screen in the config
        '''
        os_info = self.utils.hassos_get_info(self, 'os/info')
        os_version = os_info['data']['version']
        os_upgrade = os_info['data']['update_available']  

        if (os_upgrade == True):
            os_version = os_version + "*"

        core_info = self.utils.hassos_get_info(self, 'core/info')
        core_version = core_info['data']['version']  
        core_upgrade = os_info['data']['update_available']
        if (core_upgrade == True):
            core_version =  core_version + "*"

        img_size = 26
        padding = 10
        textbox_x = img_size + padding

        # Get HA Logo and Resize
        logo = self.img.resize([img_size, img_size])
        logo = ImageOps.invert(logo)  

        # Merge HA Logo with Canvas.
        self.display.image.paste(logo,(-2,3))
        self.display.draw.line([(textbox_x, 16),(123,16)], fill=255, width=1)

        ln1 = self.utils.get_hostname()
        ln1_font = self.font(size=9, is_bold=True)
        self.display.draw.text((textbox_x, 2), ln1, font=ln1_font, fill=255)

        # Write Test, Eventually will get from HA API.
        ln2 = 'OS '+ os_version + ' - ' + core_version
        ln2_font = self.font()
        self.display.draw.text((textbox_x, 20), ln2, font=ln2_font, fill=255)

        self.render_with_defaults()

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

class StatsScreen(BaseScreen):
    def set_temp_unit(self, unit):
        unit = str(unit).upper()
        if unit in ['C', 'F']:
            self.temp_unit = unit

    def get_temp(self):
        temp =  float(Utils.shell_cmd("cat /sys/class/thermal/thermal_zone0/temp")) / 1000.00

        if (hasattr(self, 'temp_unit') and self.temp_unit == 'F'):
            temp = "%0.2f °F " % (temp * 9.0 / 5.0 + 32)
        else:
            temp = "%0.2f °C " % (temp)

        return temp

    def render(self):
        self.display.prepare()
                
        ipv4 = self.utils.get_ip()
        core_stats = HassioUtils().hassos_get_info('core/stats', self.config)	
        cpu = core_stats["data"]['cpu_percent']
        temp = self.get_temp()
        mem = Utils.shell_cmd("free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'")
        storage =  Utils.shell_cmd("df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'")

        if(self.display.icon_stats == 'text'):
            self.display.draw.text((0, 0), "IP: " + ipv4, font=self.font(16), fill=255)
            self.display.draw.text((0, 16), "CPU: " + str(cpu) + "LA", font=self.font(16), fill=255)
            self.display.draw.text((80, 16), temp, font=self.font(16), fill=255)
            self.display.draw.text((0, 32), mem, font=self.font(16), fill=255)
            self.display.draw.text((0, 48), storage, font=self.font(16), fill=255)
        else:
            storage =  Utils.shell_cmd("df -h | awk '$NF==\"/\"{printf \"%d/%dGB\", $3,$2}'")
            mem = Utils.shell_cmd("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'")
            self.display.draw.text((0, 3), chr(62609), font=self.font(18, is_bold=False, is_icon=True), fill=255)
            self.display.draw.text((65, 3), chr(62776), font=self.font(18, is_bold=False, is_icon=True), fill=255)
            self.display.draw.text((0, 23), chr(63426), font=self.font(18, is_bold=False, is_icon=True), fill=255)
            self.display.draw.text((65, 23), chr(62171), font=self.font(18, is_bold=False, is_icon=True), fill=255)
            self.display.draw.text((0, 43), chr(61931), font=self.font(18, is_bold=False, is_icon=True), fill=255)
            self.display.draw.text((19, 3), str(temp), font=self.font(16), fill=255)  
            self.display.draw.text((87, 3), str(mem), font=self.font(16), fill=255)
            self.display.draw.text((19, 23), str(storage), font=self.font(16), fill=255)
            self.display.draw.text((87, 23), str(cpu) + "LA", font=self.font(16), fill=255)
            self.display.draw.text((19, 43), ipv4, font=self.font(16), fill=255)

        self.display.show()
        time.sleep(self.duration)
