from threading import Timer, Lock
from ..core.util import Bindable, log_call
from ..core.target_controller import TargetController
from .common import config
from . import gui


class PowerControlMixin(TargetController):
    """ Power on when playing starts and show a notification warning to poweroff when idling """
    notification_timeout = 10
    _playing_lock = Lock
    _playing = False
    _idle_timer_lock = Lock
    _idle_timer = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._playing_lock = self._playing_lock()
        self._idle_timer_lock = self._idle_timer_lock()
        self.target.preload_features.update((config.source, config.power))
        self.target.preload_features.add("name")
        self.target.bind(
            on_feature_change = self.on_target_feature_change,
            on_disconnected = self.close_power_notifications)
        self._power_notifications = []
        self._poweron_n = gui.Notification(
            buttons=[
                ("Don't show again", lambda:self.item_poweron.set_active(False)),
                ("Cancel", lambda:None),
                ("OK", self.poweron)],
            timeout_action=self.poweron)
        self._power_notifications.append(self._poweron_n)
        self._poweroff_n = gui.Notification(
            buttons=[
                ("Don't show again", lambda:self.item_poweroff.set_active(False)),
                ("Cancel", lambda:None),
                #("Snooze", self.snooze_notification),
                ("OK", self.poweroff)],
            timeout_action=self.poweroff, default_click_action=self.snooze_notification)
        self._power_notifications.append(self._poweroff_n)
        for n in self._power_notifications: n.set_timeout(self.notification_timeout*1000)

    def on_target_idling(self, idle):
        if idle: self.on_idle()
        else: self.on_unidle()

    def on_start_playing(self):
        """ start playing locally, e.g. via pulse """
        super().on_start_playing()
        self.on_unidle()

    def on_stop_playing(self):
        """ stop playing locally """
        super().on_stop_playing()
        # execute on_idle() if target is not playing
        try: target_playing = (
            self.target.features[config.idle].isset() and self.target.features[config.idle].get() == False)
        except (ConnectionError, KeyError): target_playing = False
        if not target_playing: self.on_idle()
        try: f = self.target.features[config.idle]
        except KeyError: pass
        else:
            if not f.isset():
                try: f.async_poll()
                except ConnectionError: pass

    def on_idle(self):
        with self._playing_lock:
            self._playing = False
            self.start_idle_timer()

    def on_unidle(self):
        """ when starting to play something locally or on amp """
        with self._playing_lock:
            self._playing = True
            self.stop_idle_timer()
        if config["power_control"]["auto_power_on"]: self.ask_poweron()

    @log_call
    def start_idle_timer(self):
        with self._idle_timer_lock:
            if self._playing or self._idle_timer and self._idle_timer.is_alive(): return
            try: timeout = config["power_control"]["poweroff_after"]*60
            except ValueError: return
            if not timeout: return
            self._idle_timer = Timer(timeout, self.ask_poweroff)
            self._idle_timer.start()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        self.stop_idle_timer()
        self.close_power_notifications()

    @log_call
    def stop_idle_timer(self):
        with self._idle_timer_lock:
            if self._idle_timer: self._idle_timer.cancel()
        self._poweroff_n.close()

    def on_target_feature_change(self, f_id, value):
        if f_id == config.power:
            if value == True: # poweron event
                self.start_idle_timer()
                self._poweron_n.close()
            elif value == False: # poweroff event
                self.stop_idle_timer()
        elif f_id == config.idle:
            self.on_target_idling(value)

    def snooze_notification(self):
        self.start_idle_timer()

    def ask_poweron(self):
        def func():
            if self.target.features[config.power].get(): return
            self._poweron_n.update("Power on %s"%self.target.features.name.get())
            self._poweron_n.show()
        self.target.schedule(func, requires=("name", config.power))

    def ask_poweroff(self):
        def func():
            if config["power_control"]["auto_power_off"] and self.can_poweroff:
                self._poweroff_n.update("Power off %s"%self.target.features.name.get())
                self._poweroff_n.show()
        self.target.schedule(func, requires=("name", config.power, config.source))

    def close_power_notifications(self):
        for n in self._power_notifications: n.close()

    def poweron(self):
        if config.source and config["target"]["source"]:
            self.target.features[config.source].remote_set(config["target"]["source"])
        self.target.features[config.power].remote_set(True)

    can_poweroff = property(
        lambda self: self.target.features[config.power].get()
        and (not config.source or self.target.features[config.source].get() == config["target"]["source"]))

    def poweroff(self):
        if not config["power_control"]["control_power_off"]: return
        self.target.schedule(lambda:self.can_poweroff and self.target.features[config.power].remote_set(False),
            requires=(config.power, config.source))

    def main_quit(self):
        """ called by SystemEvents """
        self.app_manager.main_quit()


