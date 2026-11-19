"""
Karel de Koala - RP2350 SuperMini CircuitPython Firmware
Study Association Sticky (Information Science, Utrecht University)

Hardware Pinout (RP2350 SuperMini, 4 MB Flash):
- WS2812 NeoPixel LED : GP16 default (also board.NEOPIXEL on waveshare_rp2350_zero UF2);
                        change NEOPIXEL_PIN_NAME to "GP23" or "GP22" if batch differs.
- Onboard LED fallback: board.LED / GP17 / GP25 (top-left mono LED labeled 25)
- Onboard BOOT Button : Only physical button on this SuperMini! Hold BOOT while plugging
                        USB-C to enter RP2350 UF2 update mode. NOTE: BOOT is wired directly
                        to QSPI Flash CSn on RP2350, so CircuitPython cannot read it as a
                        runtime button while executing from Flash (XIP).
- Start/Stop Toggle Btn : Optional external tactile switch on GP15 (to GND) — or GP24!
                        Press once to Show (climb from taskbar) or Hide/Close (dive back behind
                        taskbar + save + exit cleanly)! Uses instant serial EVENT:TOGGLE_KAREL when
                        connected, or Win+R -> launch_karel.bat --toggle when Karel is closed.
- Hardware Boop / RUN : No onboard RST tactile button on this 1-button PCB; re-plugging USB-C
                        wakes/boops an already-open Karel via 127.0.0.1:42421, and optional
                        external RUN reset (RESET_PIN) also listens briefly for KAREL_PING to
                        send EVENT:RST_BOOP without popping up Win+R.
- Dev / Safe Mode     : Hold outer pin GP0 (or GP24) to GND at plug-in to skip Win+R HID.
- Optional Touch Pad  : GP2 (Pet Karel -> EVENT:PET; on RP2350 requires pull-up to 3.3V)
- Optional Action Btn : GP1 / Touch GP3 (short=FEED, double=COFFEE, long 1.5s=MINIGAME)
"""

import math
import time
import board
import digitalio
import touchio
import usb_cdc

try:
    import microcontroller
except ImportError:
    microcontroller = None

try:
    import neopixel
except ImportError:
    neopixel = None

# ==============================================================================
# Hardware Configuration (1-line toggle: "GP16" RP2350 SuperMini / "GP23" clone)
# ==============================================================================
NEOPIXEL_PIN_NAME = "GP16"

PET_TOUCH_PIN_NAME = "GP2"
ACTION_BTN_PIN_NAME = "GP1"
BACKUP_TOUCH_PIN_NAME = "GP3"
USR_BTN_PIN_NAME = "GP24"
TOGGLE_BTN_PIN_NAME = "GP15"

LONG_PRESS_SEC = 1.5
DOUBLE_PRESS_WINDOW_SEC = 0.30
DEBOUNCE_SEC = 0.03
PET_COOLDOWN_SEC = 0.40


def resolve_pin(pin_name):
    """Resolve a pin name from board or microcontroller.pin cleanly."""
    pin = getattr(board, pin_name, None)
    if pin is None and microcontroller is not None and pin_name.startswith("GP"):
        pin = getattr(microcontroller.pin, "GPIO" + pin_name[2:], None)
    return pin


def check_dev_mode():
    """Return True if Dev/Safe Mode was flagged by boot.py or GP0/GP24 is held LOW."""
    if microcontroller is not None:
        try:
            if microcontroller.nvm[0] == 1:
                return True
        except Exception:
            pass
    for name in ("GP0", "GP24"):
        pin = resolve_pin(name)
        if pin is None:
            continue
        dio = None
        try:
            dio = digitalio.DigitalInOut(pin)
            dio.direction = digitalio.Direction.INPUT
            dio.pull = digitalio.Pull.UP
            time.sleep(0.005)
            if not dio.value:
                return True
        except Exception:
            pass
        finally:
            if dio is not None:
                try:
                    dio.deinit()
                except Exception:
                    pass
    return False


def is_reset_pin_boot():
    """Return True when the board rebooted via external RUN / RESET_PIN."""
    if microcontroller is None:
        return False
    try:
        cpu = getattr(microcontroller, "cpu", None)
        rr = getattr(microcontroller, "ResetReason", None)
        if cpu is not None and rr is not None:
            return cpu.reset_reason == getattr(rr, "RESET_PIN", object())
    except Exception:
        pass
    return False


class TouchOrSwitchInput:
    """Wrapper around touchio.TouchIn (with RP2350 Pull.UP support) and digital Pull.UP fallback."""

    def __init__(self, pin_name):
        self.touch = None
        self.dio = None
        pin = resolve_pin(pin_name)
        if pin is None:
            return
        try:
            # RP2350 requires an external 3.3V pull-up and pull=digitalio.Pull.UP (E9 erratum)
            self.touch = touchio.TouchIn(pin, pull=digitalio.Pull.UP)
        except Exception:
            try:
                self.touch = touchio.TouchIn(pin)
            except Exception:
                try:
                    self.dio = digitalio.DigitalInOut(pin)
                    self.dio.direction = digitalio.Direction.INPUT
                    self.dio.pull = digitalio.Pull.UP
                except Exception:
                    self.dio = None

    @property
    def active(self):
        if self.touch is not None:
            try:
                return bool(self.touch.value)
            except Exception:
                return False
        if self.dio is not None:
            return not self.dio.value
        return False


class MultiPressButton:
    """Debounce and classify short, double, and long button presses uniformly."""

    def __init__(self, short_ev, double_ev, long_ev):
        self.short_ev = short_ev
        self.double_ev = double_ev
        self.long_ev = long_ev
        self.prev = False
        self.press_start = 0.0
        self.long_sent = False
        self.pending_clicks = 0
        self.last_release = 0.0

    def update(self, pressed, now):
        """Return emitted event name (or None) on this polling step."""
        emitted = None
        if pressed and not self.prev:
            self.press_start = now
            self.long_sent = False
        elif pressed and self.prev:
            if not self.long_sent and (now - self.press_start) >= LONG_PRESS_SEC:
                self.long_sent = True
                self.pending_clicks = 0
                emitted = self.long_ev
        elif not pressed and self.prev:
            held = now - self.press_start
            if not self.long_sent and held >= DEBOUNCE_SEC:
                self.pending_clicks += 1
                self.last_release = now
                if self.pending_clicks >= 2:
                    self.pending_clicks = 0
                    emitted = self.double_ev
        self.prev = pressed
        if emitted is None and self.pending_clicks == 1 and (now - self.last_release) >= DOUBLE_PRESS_WINDOW_SEC:
            self.pending_clicks = 0
            emitted = self.short_ev
        return emitted


def _init_digital_in(pin):
    if pin is None:
        return None
    try:
        dio = digitalio.DigitalInOut(pin)
        dio.direction = digitalio.Direction.INPUT
        dio.pull = digitalio.Pull.UP
        return dio
    except Exception:
        return None


def init_neopixel():
    """Initialize onboard WS2812 RGB LED across RP2350 SuperMini batches."""
    if neopixel is None:
        return None
    candidates = [resolve_pin(NEOPIXEL_PIN_NAME), getattr(board, "NEOPIXEL", None), resolve_pin("GP16"), resolve_pin("GP23")]
    for pin in candidates:
        if pin is None:
            continue
        try:
            px = neopixel.NeoPixel(pin, 1, brightness=0.35, auto_write=False)
            px[0] = (0, 0, 0)
            px.show()
            return px
        except Exception:
            pass
    return None


def init_mono_led():
    """Optional monochrome status LED fallback on boards without WS2812."""
    for name in ("LED", "GP17", "GP25"):
        pin = resolve_pin(name)
        if pin is None:
            continue
        try:
            led = digitalio.DigitalInOut(pin)
            led.direction = digitalio.Direction.OUTPUT
            led.value = True
            return led
        except Exception:
            pass
    return None


def wheel(pos):
    """Generate rainbow RGB tuple for 0..255 color wheel position."""
    pos = int(pos) & 255
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def scale_color(rgb, factor):
    factor = max(0.0, min(1.0, factor))
    return (int(rgb[0] * factor), int(rgb[1] * factor), int(rgb[2] * factor))


def update_led(px, state, now, burst_type, burst_until, mono_led=None):
    """Non-blocking WS2812 & monochrome LED animation renderer."""
    if mono_led is not None:
        try:
            if state == "HUNGRY":
                mono_led.value = (now % 1.0) < 0.2
            elif state == "SLEEP":
                mono_led.value = (now % 2.0) < 0.1
            elif state in ("HYPER", "PARTY") or now < burst_until:
                mono_led.value = (int(now * 10) % 2) == 0
            else:
                mono_led.value = True
        except Exception:
            pass

    if px is None:
        return

    if now < burst_until:
        remaining = burst_until - now
        if burst_type == "HEART":
            tick = int(now * 24) % 4
            cols = ((255, 220, 240), (255, 90, 145), (255, 255, 255), (255, 122, 160))
            px[0] = cols[tick]
        elif burst_type == "COOLDOWN":
            tick = int(now * 16) % 2
            px[0] = (255, 130, 0) if tick == 0 else (25, 10, 0)
        elif burst_type == "BOOP":
            px[0] = wheel((now * 420.0) % 256)
        else:
            pulse = 0.35 + 0.65 * abs(math.sin(remaining * 8.0))
            px[0] = scale_color((255, 105, 155), pulse)
        px.show()
        return

    if state == "DEV":
        px[0] = (0, 255, 255)
    elif state == "HAPPY":
        breath = 0.20 + 0.80 * (0.5 + 0.5 * math.sin(now * 2.2))
        px[0] = scale_color((178, 27, 33), breath)
    elif state == "HUNGRY":
        phase = now % 2.0
        on = (0.0 <= phase < 0.14) or (0.26 <= phase < 0.40)
        px[0] = (255, 130, 0) if on else (20, 8, 0)
    elif state == "HYPER":
        px[0] = wheel((now * 280.0) % 256)
    elif state == "SLEEP":
        breath = 0.15 + 0.60 * (0.5 + 0.5 * math.sin(now * 1.1))
        px[0] = scale_color((14, 38, 135), breath)
    elif state == "STUDY":
        breath = 0.25 + 0.55 * (0.5 + 0.5 * math.sin(now * 1.6))
        px[0] = scale_color((245, 165, 35), breath)
    elif state == "QUIET":
        px[0] = (18, 32, 48)
    elif state == "BYE":
        breath = 0.06 + 0.14 * (0.5 + 0.5 * math.sin(now * 0.9))
        px[0] = scale_color((178, 27, 33), breath)
    elif state == "PARTY":
        palette = ((255, 0, 90), (0, 255, 255), (255, 220, 0), (170, 0, 255), (0, 255, 100), (255, 255, 255))
        idx = int(now * 12.0) % len(palette)
        px[0] = palette[idx] if int(now * 24.0) % 2 == 0 else scale_color(palette[idx], 0.25)
    else:
        breath = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(now * 2.0))
        px[0] = scale_color((178, 27, 33), breath)
    px.show()


def send_serial_line(line, force=False):
    """Write a newline-terminated message over USB CDC Data Serial."""
    data_port = getattr(usb_cdc, "data", None)
    if data_port is None:
        return
    if not force and not data_port.connected:
        return
    try:
        data_port.timeout = 0
        data_port.write((line.rstrip("\r\n") + "\n").encode("utf-8"))
    except Exception:
        pass


def _poll_serial_cmds(rx_buffer, led_state, burst_type, burst_until, now):
    """Read incoming serial lines; return (rx_buffer, led_state, burst_type, burst_until, pinged, host_seen)."""
    pinged = False
    host_seen = False
    data_port = getattr(usb_cdc, "data", None)
    if data_port is not None and data_port.in_waiting > 0:
        try:
            chunk = data_port.read(data_port.in_waiting)
            if chunk:
                rx_buffer += chunk.decode("utf-8")
                while "\n" in rx_buffer:
                    raw_line, rx_buffer = rx_buffer.split("\n", 1)
                    cmd = raw_line.strip().upper()
                    if not cmd:
                        continue
                    host_seen = True
                    if cmd == "KAREL_PING":
                        pinged = True
                        send_serial_line("KAREL_PONG", force=True)
                    elif cmd.startswith("STATE:"):
                        new_state = cmd.split(":", 1)[1].strip()
                        if new_state in ("HAPPY", "HUNGRY", "HYPER", "SLEEP", "STUDY", "QUIET", "PARTY", "BYE"):
                            led_state = new_state
                    elif cmd == "EVENT:HEART":
                        burst_type = "HEART"
                        burst_until = now + 1.0
                    elif cmd == "EVENT:COOLDOWN":
                        burst_type = "COOLDOWN"
                        burst_until = now + 0.45
        except Exception:
            rx_buffer = ""
    return rx_buffer, led_state, burst_type, burst_until, pinged, host_seen


def main():
    px = init_neopixel()
    mono_led = init_mono_led()
    dev_mode = check_dev_mode()
    rst_boot = is_reset_pin_boot()
    led_state = "DEV" if dev_mode else "HAPPY"
    burst_type = "BOOP" if rst_boot else None
    burst_until = (time.monotonic() + 1.4) if rst_boot else 0.0
    rx_buffer = ""

    update_led(px, led_state, time.monotonic(), burst_type, burst_until, mono_led)

    if dev_mode:
        print("[KAREL] Dev/Safe Mode active (GP0/GP24).")
    else:
        try:
            import supervisor
            supervisor.runtime.autoreload = False
        except Exception:
            pass
        # Briefly listen for an already-running desktop companion (or opt-in tray watcher)
        # so re-plugging triggers an immediate hardware boop + LED greeting.
        ping_deadline = time.monotonic() + (2.0 if rst_boot else 2.5)
        while time.monotonic() < ping_deadline:
            now = time.monotonic()
            rx_buffer, led_state, burst_type, burst_until, pinged, host_seen = _poll_serial_cmds(
                rx_buffer, led_state, burst_type, burst_until, now,
            )
            if pinged or host_seen:
                if pinged:
                    send_serial_line("EVENT:RST_BOOP", force=True)
                    burst_type = "BOOP"
                    burst_until = now + 1.5
                break
            update_led(px, led_state, now, burst_type, burst_until, mono_led)
            time.sleep(0.025)

    pet_sensor = TouchOrSwitchInput(PET_TOUCH_PIN_NAME)
    backup_action_sensor = TouchOrSwitchInput(BACKUP_TOUCH_PIN_NAME)
    action_btn = _init_digital_in(resolve_pin(ACTION_BTN_PIN_NAME))
    usr_pin = getattr(board, "BUTTON", None) or resolve_pin(USR_BTN_PIN_NAME)
    usr_btn = _init_digital_in(usr_pin)
    toggle_btn = _init_digital_in(resolve_pin(TOGGLE_BTN_PIN_NAME))

    action_tracker = MultiPressButton("EVENT:FEED", "EVENT:COFFEE", "EVENT:MINIGAME")
    usr_tracker = MultiPressButton("EVENT:TOGGLE_KAREL", "EVENT:DISCO", "EVENT:GIFT")
    toggle_tracker = MultiPressButton("EVENT:TOGGLE_KAREL", "EVENT:TOGGLE_KAREL", "EVENT:DISCO")

    prev_pet = False
    last_pet_time = 0.0
    last_host_rx = 0.0

    while True:
        now = time.monotonic()
        rx_buffer, led_state, burst_type, burst_until, _, host_seen = _poll_serial_cmds(
            rx_buffer, led_state, burst_type, burst_until, now,
        )
        if host_seen:
            last_host_rx = now

        def _handle_toggle_press():
            nonlocal led_state, burst_type, burst_until, last_host_rx
            data_port = getattr(usb_cdc, "data", None)
            desktop_alive = (
                data_port is not None
                and data_port.connected
                and led_state != "BYE"
                and (now - last_host_rx) < 4.5
            )
            if desktop_alive:
                send_serial_line("EVENT:TOGGLE_KAREL", force=True)
                led_state = "BYE"
                burst_type = "HEART"
                burst_until = now + 0.55
            else:
                send_serial_line("EVENT:TOGGLE_KAREL", force=True)
                led_state = "HAPPY"
                burst_type = "BOOP"
                burst_until = now + 0.8

        pet_now = pet_sensor.active
        if pet_now and not prev_pet and (now - last_pet_time) >= PET_COOLDOWN_SEC:
            last_pet_time = now
            send_serial_line("EVENT:PET")
            burst_type = "PET"
            burst_until = now + 0.85
        prev_pet = pet_now

        btn1_pressed = (action_btn is not None and not action_btn.value) or backup_action_sensor.active
        ev1 = action_tracker.update(btn1_pressed, now)
        if ev1:
            send_serial_line(ev1)
            if ev1 == "EVENT:MINIGAME":
                burst_type = "HEART"
                burst_until = now + 0.45

        btn2_pressed = usr_btn is not None and not usr_btn.value
        ev2 = usr_tracker.update(btn2_pressed, now)
        if ev2 == "EVENT:TOGGLE_KAREL":
            _handle_toggle_press()
        elif ev2:
            send_serial_line(ev2)
            burst_type = "BOOP"
            burst_until = now + 0.8

        t_pressed = toggle_btn is not None and not toggle_btn.value
        ev_t = toggle_tracker.update(t_pressed, now)
        if ev_t == "EVENT:TOGGLE_KAREL":
            _handle_toggle_press()
        elif ev_t:
            send_serial_line(ev_t)
            burst_type = "BOOP"
            burst_until = now + 0.8

        update_led(px, led_state, now, burst_type, burst_until, mono_led)
        time.sleep(0.025)


if __name__ == "__main__":
    main()
