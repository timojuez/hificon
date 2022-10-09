import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject
from threading import Thread
from ..common import gtk
from ...core.transmission.discovery import discover_targets, get_name
from ...core.config import config
from ... import Target
from ...amp import AbstractAmp


class UriSettingMode:
    RADIO_NAME = ""

    def __init__(self, target_setup):
        self.target_setup = target_setup
        self.radio = self.target_setup.builder.get_object(self.RADIO_NAME)

    def is_active(self): return self.radio.get_active()
    def get_uri(self): raise NotImplementedError()
    def set_uri(self, uri, active_mode): raise NotImplementedError()
    def __str__(self): return self.RADIO_NAME
    def __eq__(self, o): return str(o) == str(self)


class DeviceListMode(UriSettingMode):
    RADIO_NAME = "devices_view_radiobutton"

    def get_uri(self):
        l, it = self.target_setup.devices_view.get_selection().get_selected()
        if it:
            name, target = l.get_value(it, 0)
            return target.uri
        else: self.target_setup.show_error("No item selected.")

    def set_uri(self, uri, active_mode):
        if active_mode and active_mode != self: return
        row = self.target_setup._add_target_to_list(Target(uri))
        path=self.target_setup.devices_list.get_path(row)
        self.target_setup.devices_view.set_cursor(path)
        self.radio.set_active(True)


class TextEditMode(UriSettingMode):
    RADIO_NAME = "uri_edit_radiobutton"

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.uri_edit = self.target_setup.builder.get_object("uri_edit")

    def get_uri(self):
        uri = self.uri_edit.get_text()
        if not uri: return self.target_setup.show_error("URI cannot be empty.")
        return uri

    def set_uri(self, uri, active_mode):
        self.uri_edit.set_text(uri)
        if active_mode == self:
            self.radio.set_active(True)


class DemoMode(UriSettingMode):
    RADIO_NAME = "demo_radiobutton"
    URI = "emulate:denon"

    def get_uri(self): return self.URI

    def set_uri(self, uri, active_mode):
        if active_mode == self:
            self.radio.set_active(True)


class DeviceListMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.devices_view = self.builder.get_object("devices_view")
        column = self.builder.get_object("devices_column")
        self.devices_list = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self.devices_view.set_model(self.devices_list)
        cell = Gtk.CellRendererText()
        column.set_cell_data_func(cell, self._set_devices_cell_text)
        column.pack_start(cell, True)

    def on_target_search_click(self, *args, **xargs):
        self.search_and_add_targets()

    def search_and_add_targets(self):
        Thread(target=self._search_and_add_targets, daemon=True, name="search_and_add_targets()").start()

    def _search_and_add_targets(self):
        gtk(lambda:self.builder.get_object("device_search_button").set_sensitive(False))()
        print("Starting search")
        try:
            discovered = [target for x in self.devices_list for name, target in x]
            for target in discover_targets():
                if target in discovered: continue
                self._add_target_to_list(target)
        finally:
            print("Finished search")
            gtk(lambda:self.builder.get_object("device_search_button").set_sensitive(True))()

    def _add_target_to_list(self, target):
        def set_name(target=target, i=len(self.devices_list)):
            if name := get_name(target):
                self.devices_list[i] = [(name, target)]
        r = self.devices_list.append([(target.uri, target)])
        Thread(target=set_name, daemon=True, name="get_target_name").start()
        return r

    def _set_devices_cell_text(self, column, cell, model, it, data):
        name, target = model.get_value(it, 0)
        cell.set_property('text', name)

    @gtk
    def on_devices_view_button_release_event(self, *args, **xargs):
        self.builder.get_object("devices_view_radiobutton").set_active(True)
        self.on_target_setup_changed()

    def _reset_target_setup(self):
        self.devices_list.clear()
        super()._reset_target_setup()


class TextEditMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.uri_edit_radio = self.builder.get_object("uri_edit_radiobutton")

    @gtk
    def on_uri_edit_button_release_event(self, *args, **xargs):
        self.uri_edit_radio.set_active(True)
        self.on_target_setup_changed()


class Base:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.apply_button = self.builder.get_object("apply_button")
        self._modes = {C:C(self) for C in (TextEditMode, DemoMode, DeviceListMode)}
        if self._first_run: self.on_first_run()

    @gtk
    def show(self): self._show()

    def _show(self):
        self._reset_target_setup()
        super().show()

    @gtk
    def reset_target_setup(self): self._reset_target_setup()

    def _reset_target_setup(self):
        uri = config["Target"]["uri"]
        target_setup_mode = config["Tray"]["target_setup_mode"]
        for m in self._modes.values():
            m.set_uri(uri, target_setup_mode)
        self.apply_button.set_sensitive(False)

    def on_device_settings_radiobutton_toggled(self, *args, **xargs):
        self.on_target_setup_changed()

    def on_target_setup_changed(self):
        self.apply_button.set_sensitive(True)

    def on_apply_device_settings(self, *args, **xargs):
        for m in self._modes.values():
            if m.is_active(): break
        uri = m.get_uri()
        if uri is None: return
        try: target = Target(uri)
        except Exception as e: return self.show_error(f"Could not create target for URI '{uri}': {e}")
        if not isinstance(target, AbstractAmp):
            return self.show_error(f"URI must refer to an amplifier: '{uri}'")

        config["Target"]["uri"] = uri
        config["Tray"]["target_setup_mode"] = str(m)
        self.hide()
        self.app_manager.run_app(uri, callback=lambda: self.app_manager.main_app.settings.show_device_settings())

    def show_device_settings(self):
        self._show()
        tab = self.builder.get_object("device_settings")
        nb = self.builder.get_object("notebook")
        for i in range(nb.get_n_pages()):
            if nb.get_nth_page(i) == tab:
                return nb.set_current_page(i)
        raise IndexError(f"{tab} not found in {nb}")

    def show_error(self, text):
        diag = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, 
            Gtk.ButtonsType.OK, text)
        diag.connect("response", lambda *_: diag.destroy())
        diag.run()

    @gtk
    def on_first_run(self):
        self.show_device_settings()
        self.search_and_add_targets()


class TargetSetup(DeviceListMixin, TextEditMixin, Base): pass

