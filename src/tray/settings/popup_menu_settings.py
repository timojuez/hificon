import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GObject
from ...core import features, config


DND_FROM_MENU_INFO = 1000 # drag n drop id
DND_FROM_AVAIL = [('a', Gtk.TargetFlags.SAME_APP, DND_FROM_MENU_INFO+1)]
DND_FROM_MENU = [('b', Gtk.TargetFlags.SAME_APP, DND_FROM_MENU_INFO)]


class AvailTreeStore(Gtk.TreeStore):
    """ Forbid dragging category items """

    def __init__(self, view, *args, **xargs):
        super().__init__(*args, **xargs)
        self._view = view

    def do_row_draggable(self, path):
        #return path.get_depth() > 1
        obj = self._view.get_model().get_value(self._view.get_model().get_iter(path), 0)
        return isinstance(obj, features.Feature)


class AvailableFeaturesList:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.available_list = self.builder.get_object("available_list")
        self.available_column = self.builder.get_object("available_column")
        self.avail_view = self.builder.get_object("avail_view")
        avail_list = AvailTreeStore(self.avail_view, GObject.TYPE_PYOBJECT)
        category = {c:avail_list.append(None, [c]) for c in self.target.feature_categories}
        for f in self.target.features.values(): avail_list.append(category[f.category], [f])
        self.avail_view.set_model(avail_list)
        cell = Gtk.CellRendererText()
        self.available_column.set_cell_data_func(cell, self._set_avail_cell_text)
        self.available_column.pack_start(cell, True)
        #self.available_column.add_attribute(cell, "text", 0)

        self.avail_view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, DND_FROM_AVAIL, Gdk.DragAction.COPY)
        self.avail_view.enable_model_drag_dest(DND_FROM_MENU, Gdk.DragAction.MOVE)

    def _set_avail_cell_text(self, column, cell, model, it, data):
        obj = model.get_value(it, 0)
        s = getattr(obj, "name", obj)
        cell.set_property('text', s)

    def on_avail_view_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        context.finish(True, True, timestamp)
        self.on_menu_change()


class SelectedFeaturesList:

    def __init__(self, *args, on_menu_settings_change=None, **xargs):
        super().__init__(*args, **xargs)
        self.on_menu_settings_change = on_menu_settings_change
        self.menu_list = self.builder.get_object("menu_list")
        self.menu_column = self.builder.get_object("menu_column")
        self.menu_view = self.builder.get_object("menu_view")
        
        self.menu_list = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self.menu_view.set_model(self.menu_list)
        cell = Gtk.CellRendererText()
        self.menu_column.set_cell_data_func(cell, self._set_menu_cell_text)
        self.menu_column.pack_start(cell, True)

        self.menu_view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, DND_FROM_MENU, Gdk.DragAction.MOVE)
        self.menu_view.enable_model_drag_dest(DND_FROM_AVAIL+DND_FROM_MENU, Gdk.DragAction.MOVE)

        self._load_tray_menu_features()

    def _update_listeners(self, f_ids):
        if not self.on_menu_settings_change: return
        features = [f for f_id in f_ids for f in [self._id_to_feature(f_id)] if f]
        self.on_menu_settings_change(features)

    def _load_tray_menu_features(self):
        features = self.config["tray_menu_features"]
        for f_id in features: self.menu_list.append([f_id])
        self._update_listeners(features)

    def _save_tray_menu_features(self, features):
        self.config["tray_menu_features"] = features

    def _id_to_feature(self, f_id):
        f_id = config.get("Amp", f_id[1:]) if f_id.startswith("@") else f_id
        return self.target.features.get(f_id)

    def _id_to_string(self, f_id):
        f = self._id_to_feature(f_id)
        return f"{f.name} ({f.category})" if f else f"{f_id} (Unavailable)"

    def _set_menu_cell_text(self, column, cell, model, it, data):
        f_id = model.get_value(it, 0)
        s = self._id_to_string(f_id)
        cell.set_property('text', s)

    def on_menu_view_drag_data_received(self, treeview, context, x, y, selection, info, timestamp):
        f_id = selection.get_text()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, pos = drop_info
            drop_before = pos in (Gtk.TreeViewDropPosition.BEFORE, Gtk.TreeViewDropPosition.INTO_OR_BEFORE)
            insert = (self.menu_list.insert_before if drop_before
                else self.menu_list.insert_after)
            insert(self.menu_list.get_iter(path), [f_id])
            #widget.stop_emission('drag_data_received')
        else:
            self.menu_list.append([f_id])
        context.finish(True, info == DND_FROM_MENU_INFO, timestamp)
        self.on_menu_change()

    def on_menu_change(self):
        f_ids = []
        it = self.menu_list.get_iter_first()
        while it:
            f_id = self.menu_list.get_value(it, 0)
            f_ids.append(f_id)
            it = self.menu_list.iter_next(it)
        self._save_tray_menu_features(f_ids)
        self._update_listeners(f_ids)

    def on_menu_view_drag_drop(self, treeview, context, x, y, time):
        context.finish(True, False, time)


class PopupMenuSettings(SelectedFeaturesList, AvailableFeaturesList):

    def on_view_drag_data_get(self, treeview, context, selection, info, timestamp):
        treeselection = treeview.get_selection()
        model, iter = treeselection.get_selected()
        obj = model.get_value(iter, 0)
        b = getattr(obj, "id", obj).encode()
        selection.set(Gdk.TARGET_STRING, 8, b)


