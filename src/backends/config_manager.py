import os
import json
import xml.etree.ElementTree as ET
from PySide6.QtCore import QObject, Signal, Property
try:
    from paths import get_writable_appdata_dir, get_resource_path
except ImportError:
    from src.paths import get_writable_appdata_dir, get_resource_path

def get_appdata_dir():
    return get_writable_appdata_dir()

class ConfigManager:
    def __init__(self, packages_dir=None):
        if packages_dir is None:
            self.packages_dir = get_resource_path("upstream_kde_widgets/packages")
        else:
            self.packages_dir = os.path.abspath(packages_dir)
        self.appdata_dir = get_appdata_dir()
        self.config_file = os.path.join(self.appdata_dir, "config.json")
        self.layout_file = os.path.join(self.appdata_dir, "layout.json")
        self.saved_configs = self._load_json(self.config_file)
        self.saved_layouts = self._load_json(self.layout_file)
        self._config_instances = {}
        self._migrate_legacy_names()

    def _migrate_legacy_names(self):
        migrated = False
        if isinstance(self.saved_layouts, dict):
            for pkg, ldata in self.saved_layouts.items():
                if isinstance(ldata, dict) and "name" in ldata and "macOS " in ldata["name"]:
                    ldata["name"] = ldata["name"].replace("macOS ", "Glass ")
                    migrated = True
        if migrated:
            self.save_layouts()

    def _load_json(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Error reading {path}: {e}")
        return {}

    def _save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Error writing {path}: {e}")

    def save_configs(self):
        # Sync values from instances
        for pkg, inst in self._config_instances.items():
            if hasattr(inst, "_values"):
                self.saved_configs[pkg] = dict(inst._values)
        self._save_json(self.config_file, self.saved_configs)

    def save_layouts(self):
        self._save_json(self.layout_file, self.saved_layouts)

    def parse_main_xml(self, pkg_name):
        xml_path = os.path.join(self.packages_dir, pkg_name, "contents", "config", "main.xml")
        defaults = {}
        if not os.path.exists(xml_path):
            return defaults
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for entry in root.iter():
                if entry.tag.split("}")[-1] == "entry":
                    name = entry.get("name")
                    etype = entry.get("type", "String")
                    default_el = None
                    for child in entry:
                        if child.tag.split("}")[-1] == "default":
                            default_el = child
                            break
                    raw_val = default_el.text.strip() if default_el is not None and default_el.text else ""
                    
                    val = raw_val
                    if etype in ("Int", "int"):
                        val = int(raw_val) if raw_val else 0
                    elif etype in ("Bool", "bool"):
                        val = raw_val.lower() in ("true", "1")
                    elif etype in ("Double", "float"):
                        val = float(raw_val) if raw_val else 0.0
                    elif etype in ("StringList", "stringlist"):
                        val = [x.strip() for x in raw_val.split(",") if x.strip()] if raw_val else []
                    defaults[name] = val
        except Exception as e:
            print(f"[ConfigManager] Error parsing {xml_path}: {e}")
        return defaults

    def get_widget_config(self, pkg_name):
        if pkg_name in self._config_instances:
            return self._config_instances[pkg_name]

        defaults = self.parse_main_xml(pkg_name)
        # Ensure common glass defaults exist even if not in main.xml
        common_defaults = {
            "styleMode": 0,
            "appearance": 0,
            "cornerRadius": 100,
            "roundnessX10": 75,
            "refractThickness": 35,
            "refractIORx100": 170,
            "refractScale": 65,
            "tintAlphaPct": 10,
            "chromaStrengthPct": 30,
            "specStrengthPct": 70,
            "blurRadiusPx": 6,
            "blurAlgorithm": 0,
            "realtimeRefraction": False,
            "opaqueBackground": True
        }
        for k, v in common_defaults.items():
            if k not in defaults:
                defaults[k] = v

        # Apply saved overrides
        if pkg_name in self.saved_configs:
            for k, v in self.saved_configs[pkg_name].items():
                defaults[k] = v

        # Build dynamic QObject class
        attrs = {"__module__": __name__}
        for k, val in defaults.items():
            sig_name = f"{k}Changed"
            sig = Signal()
            attrs[sig_name] = sig

            def make_getter(prop_name):
                return lambda self: self._values.get(prop_name)

            def make_setter(prop_name, s_name):
                def setter(self, v):
                    if self._values.get(prop_name) != v:
                        self._values[prop_name] = v
                        getattr(self, s_name).emit()
                return setter

            ptype = type(val) if val is not None else str
            if ptype not in (int, bool, float, str, list):
                ptype = "QVariant"
            attrs[k] = Property(ptype, make_getter(k), make_setter(k, sig_name), notify=sig)

        def __init__(self, parent=None):
            QObject.__init__(self, parent)
            self._values = dict(defaults)

        attrs["__init__"] = __init__
        cls = type(f"{pkg_name.replace('-', '_')}_Config", (QObject,), attrs)
        inst = cls()
        self._config_instances[pkg_name] = inst
        return inst

    def set_widget_config(self, pkg_name, prop_name, value):
        cfg = self.get_widget_config(pkg_name)
        if hasattr(cfg, prop_name):
            setattr(cfg, prop_name, value)
        if pkg_name not in self.saved_configs:
            self.saved_configs[pkg_name] = {}
        self.saved_configs[pkg_name][prop_name] = value
        self.save_configs()

    def get_layout(self, pkg_name, default_w=300, default_h=300, default_x=100, default_y=100, default_visible=False):
        if pkg_name in self.saved_layouts:
            return self.saved_layouts[pkg_name]
        layout = {
            "x": default_x,
            "y": default_y,
            "width": default_w,
            "height": default_h,
            "scale": 1.0,
            "visible": default_visible,
            "locked": False,
            "gridSnap": 16
        }
        self.saved_layouts[pkg_name] = layout
        return layout

    def update_layout(self, pkg_name, **kwargs):
        layout = self.get_layout(pkg_name)
        for k, v in kwargs.items():
            layout[k] = v
        self.saved_layouts[pkg_name] = layout
        self.save_layouts()
