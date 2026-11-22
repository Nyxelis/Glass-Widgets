import os
import json
import uuid
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
        self._instance_config_objs = {}
        self._migrate_to_instance_format()

    @staticmethod
    def _friendly_name(pkg_name):
        titles = {
            "calendar": "Glass Calendar",
            "clock-analog": "Glass Clock I",
            "clock-analog-2": "Glass Clock II",
            "clock-analog-3": "Glass Clock III",
            "clock-digital": "Glass Clock Digital",
            "clock-glass-text": "Glass Text Clock",
            "city-1": "Glass City I",
            "city-2": "Glass City II",
            "city-3": "Glass City III",
            "city-digital": "Glass City Digital",
            "music": "Glass Music",
            "timer": "Glass Timer",
            "weather": "Glass Weather",
            "weather-panel": "Glass Weather Panel",
            "test-glass": "Glass Text",
            "test-timer": "Glass Timer Test"
        }
        return titles.get(pkg_name, pkg_name)

    def _migrate_to_instance_format(self):
        migrated = False
        if not isinstance(self.saved_layouts, dict) or "instances" not in self.saved_layouts:
            legacy_data = dict(self.saved_layouts) if isinstance(self.saved_layouts, dict) else {}
            new_layouts = {"version": 2, "instances": {}}

            visible_items = [(pkg, data) for pkg, data in legacy_data.items() if isinstance(data, dict) and data.get("visible", False)]
            if visible_items:
                for pkg, ldata in visible_items:
                    inst_id = f"{pkg}_1"
                    name = ldata.get("name") or self._friendly_name(pkg)
                    if "macOS " in name:
                        name = name.replace("macOS ", "Glass ")
                    
                    inst_cfg = dict(self.saved_configs.get(pkg, {}))
                    new_layouts["instances"][inst_id] = {
                        "id": inst_id,
                        "type": pkg,
                        "name": name,
                        "x": int(ldata.get("x", 100)),
                        "y": int(ldata.get("y", 100)),
                        "width": int(ldata.get("width", 300)),
                        "height": int(ldata.get("height", 300)),
                        "scale": float(ldata.get("scale", 1.0)),
                        "visible": True,
                        "locked": bool(ldata.get("locked", False)),
                        "gridSnap": int(ldata.get("gridSnap", 16)),
                        "config": inst_cfg
                    }
            else:
                new_layouts["instances"]["calendar_1"] = {
                    "id": "calendar_1",
                    "type": "calendar",
                    "name": "Glass Calendar",
                    "x": 800, "y": 592, "width": 512, "height": 256,
                    "scale": 0.75, "visible": True, "locked": False, "gridSnap": 16,
                    "config": {}
                }
                new_layouts["instances"]["clock-analog_1"] = {
                    "id": "clock-analog_1",
                    "type": "clock-analog",
                    "name": "Glass Clock I",
                    "x": 100, "y": 120, "width": 300, "height": 300,
                    "scale": 1.0, "visible": True, "locked": False, "gridSnap": 16,
                    "config": {}
                }
            self.saved_layouts = new_layouts
            migrated = True

        if isinstance(self.saved_layouts, dict) and "instances" in self.saved_layouts:
            for inst_id, inst in self.saved_layouts["instances"].items():
                if isinstance(inst, dict) and "name" in inst and "macOS " in inst["name"]:
                    inst["name"] = inst["name"].replace("macOS ", "Glass ")
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
        self._save_json(self.config_file, self.saved_configs)

    def save_layouts(self):
        self._save_json(self.layout_file, self.saved_layouts)

    def get_instances(self):
        if not isinstance(self.saved_layouts, dict):
            self.saved_layouts = {"version": 2, "instances": {}}
        if "instances" not in self.saved_layouts:
            self.saved_layouts["instances"] = {}
        return self.saved_layouts["instances"]

    def get_instance(self, instance_id):
        return self.get_instances().get(instance_id)

    def create_instance(self, pkg_name, name=None, x=None, y=None, width=None, height=None, scale=1.0):
        instances = self.get_instances()
        count = sum(1 for inst in instances.values() if inst.get("type") == pkg_name) + 1
        inst_id = f"{pkg_name}_{uuid.uuid4().hex[:6]}"

        if name is None:
            base_title = self._friendly_name(pkg_name)
            name = f"{base_title} #{count}"

        defaults_dims = {
            "weather": (480, 240),
            "calendar": (512, 256),
            "music": (448, 240),
            "clock-digital": (400, 224),
            "test-glass": (352, 192),
            "timer": (224, 224),
            "city-3": (208, 208),
            "weather-panel": (384, 416),
            "city-digital": (640, 300),
        }
        def_w, def_h = defaults_dims.get(pkg_name, (300, 300))
        w = width if width is not None else def_w
        h = height if height is not None else def_h
        cur_x = x if x is not None else 100
        cur_y = y if y is not None else 100

        inst_cfg = dict(self.saved_configs.get(pkg_name, {}))

        new_inst = {
            "id": inst_id,
            "type": pkg_name,
            "name": name,
            "x": int(cur_x),
            "y": int(cur_y),
            "width": int(w),
            "height": int(h),
            "scale": float(scale),
            "visible": True,
            "locked": False,
            "gridSnap": 16,
            "config": inst_cfg
        }
        instances[inst_id] = new_inst
        self.save_layouts()
        return inst_id

    def delete_instance(self, instance_id):
        instances = self.get_instances()
        if instance_id in instances:
            del instances[instance_id]
            self._instance_config_objs.pop(instance_id, None)
            self.save_layouts()

    def update_instance_layout(self, instance_id, **kwargs):
        inst = self.get_instance(instance_id)
        if inst:
            for k, v in kwargs.items():
                inst[k] = v
            self.save_layouts()

    def set_instance_config(self, instance_id, prop_name, value):
        inst = self.get_instance(instance_id)
        if inst:
            if "config" not in inst:
                inst["config"] = {}
            inst["config"][prop_name] = value
            cfg_obj = self._instance_config_objs.get(instance_id)
            if cfg_obj and hasattr(cfg_obj, prop_name):
                setattr(cfg_obj, prop_name, value)
            self.save_layouts()

    def get_instance_config_val(self, instance_id, prop_name, default=None):
        inst = self.get_instance(instance_id)
        if inst and "config" in inst:
            return inst["config"].get(prop_name, default)
        return default

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

    def get_instance_config(self, instance_id, pkg_name):
        if instance_id in self._instance_config_objs:
            return self._instance_config_objs[instance_id]

        defaults = self.parse_main_xml(pkg_name)
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

        if pkg_name in self.saved_configs:
            for k, v in self.saved_configs[pkg_name].items():
                defaults[k] = v

        inst = self.get_instance(instance_id)
        if inst and "config" in inst:
            for k, v in inst["config"].items():
                defaults[k] = v

        attrs = {"__module__": __name__}
        for k, val in defaults.items():
            sig_name = f"{k}Changed"
            sig = Signal()
            attrs[sig_name] = sig

            def make_getter(prop_name):
                return lambda s: s._values.get(prop_name)

            def make_setter(prop_name, s_name):
                def setter(s, v):
                    if s._values.get(prop_name) != v:
                        s._values[prop_name] = v
                        getattr(s, s_name).emit()
                        if inst and "config" in inst:
                            inst["config"][prop_name] = v
                            self.save_layouts()
                return setter

            ptype = type(val) if val is not None else str
            if ptype not in (int, bool, float, str, list):
                ptype = "QVariant"
            attrs[k] = Property(ptype, make_getter(k), make_setter(k, sig_name), notify=sig)

        def __init__(s, parent=None):
            QObject.__init__(s, parent)
            s._values = dict(defaults)

        attrs["__init__"] = __init__
        safe_name = f"Inst_{instance_id.replace('-', '_')}_{pkg_name.replace('-', '_')}"
        cls = type(safe_name, (QObject,), attrs)
        inst_obj = cls()
        self._instance_config_objs[instance_id] = inst_obj
        return inst_obj

    def get_widget_config(self, pkg_name):
        return self.get_instance_config(f"{pkg_name}_default", pkg_name)

    def set_widget_config(self, pkg_name, prop_name, value):
        if pkg_name not in self.saved_configs:
            self.saved_configs[pkg_name] = {}
        self.saved_configs[pkg_name][prop_name] = value
        self.save_configs()

    def get_layout(self, pkg_name, **kwargs):
        for inst_id, inst in self.get_instances().items():
            if inst.get("type") == pkg_name:
                return inst
        return {}

    def update_layout(self, pkg_name, **kwargs):
        for inst_id, inst in self.get_instances().items():
            if inst.get("type") == pkg_name:
                self.update_instance_layout(inst_id, **kwargs)
                return
