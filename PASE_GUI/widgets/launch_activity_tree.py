"""
LaunchActivityTree
==================
A read-only, live panel that reflects what each launch category ACTUALLY
brought up on the ROS graph (not merely what the config files declare):

  * It queries the live ROS 2 graph (via the shared ROS2Manager node) for the
    set of running nodes and groups them per category.
  * The config YAMLs are used only to know how many nodes a category is
    EXPECTED to launch, so health can be classified:
        all expected nodes up      -> "all"      (teal)
        some up, some missing      -> "partial"  (amber / warning)
        category launched, none up -> "none"     (red / failure)
  * Only nodes that are actually running are listed under their category;
    stopping a category removes its branch.

No hard ROS dependency at import time: the live-node provider is wrapped in
try/except and can be injected (used for headless tests). If the graph can't
be reached the panel degrades to a config-derived listing.
"""
import os

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

try:
    from ruamel.yaml import YAML
    _YAML = YAML(typ="safe")
except Exception:  # pragma: no cover
    _YAML = None

_C = {
    "bg_card": "#141B23", "border": "#2A3543", "text": "#E8EEF4",
    "text_muted": "#94A2B3", "text_faint": "#5E6E80", "spine": "#3A4A5E",
}

# status -> accent colour
STATUS_COLOR = {"all": "#2DD4BF", "partial": "#FBBF24", "none": "#F2706B"}

# Per-category base accent (used when status is "all"); partial/none override.
CATEGORY_COLORS = {
    "Synchronizer":     "#F97316",   # orange      — clearly distinct from teal
    "Gait Detection":   "#A3E635",   # lime green  — clearly distinct from orange/teal
    "Motion Planner":   "#60A5FA",   # sky blue
    "Profile Manager":  "#A78BFA",   # purple
    "HIL Optimizer":    "#FBBF24",   # amber
    "Cost Computation": "#F472B6",   # pink
}

# ---- node naming scheme (matches the exo_stack launch files) ----------------
# Live ROS node names are the YAML key names with a type suffix, so categories
# never collide even when they share a key:
#   Gait Detection   -> "<event_key>_event"     (keys in gait_events.yaml)
#   Motion Planner   -> "<planner_key>_planner" (keys in mplanner.yaml)
#   Profile Manager  -> "<profile_key>_profile" (keys in profile.yaml)
#   HIL Optimizer    -> "<profile>_hil"         (profiles in HIL mode)
#   Cost Computation -> "<profile>_cost"        (profiles with a cost fn)
#   Synchronizer     -> standalone node "generic_sync_node"
NODE_SUFFIX = {
    "Gait Detection":  "_event",
    "Motion Planner":  "_planner",
    "Profile Manager": "_profile",
}
SYNC_NODE = "generic_sync_node"


def _qc(hex_str, a=255):
    c = QColor(hex_str)
    c.setAlpha(a)
    return c


class LaunchActivityTree(QWidget):
    HEADER_H = 34
    CAT_H = 26
    CHILD_H = 21
    PAD = 14
    SPINE_X = 22

    def __init__(self, parent=None, config_dir=None, node_names_provider=None):
        super().__init__(parent)
        self.config_dir = config_dir or os.path.expanduser("~/exo_stack_resources/config")
        self._provider = node_names_provider          # injectable for tests
        self._cache = {}                              # yaml path -> (mtime, data)
        self._rows = []                               # [(cat, color, status, [nodes], (m,n))]
        self.status_by_category = {}                  # cat -> "all"/"partial"/"none"
        self._graph_ok = True
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # ---------- live ROS graph ----------
    def _live_nodes(self):
        if self._provider is not None:
            try:
                return self._provider()
            except Exception:
                return None
        try:
            from widgets.ros_manager import ROS2Manager
            node = ROS2Manager.instance().node
            out = []
            for name, ns in node.get_node_names_and_namespaces():
                ns = ns or "/"
                full = (ns.rstrip("/") + "/" + name) if ns != "/" else ("/" + name)
                out.append(full)
            return out
        except Exception:
            return None

    # ---------- config-derived expected nodes ----------
    def _read_keys(self, fname, top_key):
        path = os.path.join(self.config_dir, fname)
        try:
            mtime = os.path.getmtime(path)
            cached = self._cache.get(path)
            if not cached or cached[0] != mtime:
                if _YAML is None:
                    return None
                with open(path) as f:
                    self._cache[path] = (mtime, _YAML.load(f) or {})
            node = self._cache[path][1].get(top_key, {})
            if hasattr(node, "keys"):
                return list(node.keys())
            if isinstance(node, list):
                return [(e.get("name") or e.get("profile_name") or f"item_{i}")
                        if isinstance(e, dict) else str(e) for i, e in enumerate(node)]
        except Exception:
            return None
        return None

    def _read_map(self, fname, top_key):
        """Like _read_keys but returns the mapping itself (or None)."""
        path = os.path.join(self.config_dir, fname)
        try:
            mtime = os.path.getmtime(path)
            cached = self._cache.get(path)
            if not cached or cached[0] != mtime:
                if _YAML is None:
                    return None
                with open(path) as f:
                    self._cache[path] = (mtime, _YAML.load(f) or {})
            node = self._cache[path][1].get(top_key, {})
            return node if hasattr(node, "keys") else None
        except Exception:
            return None

    def _profiles_with(self, kind):
        """Profile keys that spawn a HIL ('<p>_hil') or cost ('<p>_cost') node."""
        profs = self._read_map("profile.yaml", "profiles") or {}
        out = []
        for p, e in profs.items():
            if not hasattr(e, "get"):
                continue
            if kind == "hil" and (e.get("mode") == "HIL"
                                  or "hil_algo" in e or "hil_output_topic" in e):
                out.append(p)
            elif kind == "cost" and ("cost_algo" in e or "cost_topic" in e):
                out.append(p)
        return out

    def expected_names(self, category):
        """Exact node names a category is expected to launch, derived from the
        config keys plus the launch-file type suffix (see NODE_SUFFIX). Returns
        None only when the backing config can't be read."""
        if category == "Synchronizer":
            return [SYNC_NODE]
        if category == "Gait Detection":
            ks = self._read_keys("gait_events.yaml", "events")
            return [f"{k}_event" for k in ks] if ks is not None else None
        if category == "Motion Planner":
            ks = self._read_keys("mplanner.yaml", "planners")
            return [f"{k}_planner" for k in ks] if ks is not None else None
        if category == "Profile Manager":
            ks = self._read_keys("profile.yaml", "profiles")
            return [f"{k}_profile" for k in ks] if ks is not None else None
        if category == "HIL Optimizer":
            return [f"{p}_hil" for p in self._profiles_with("hil")]
        if category == "Cost Computation":
            return [f"{p}_cost" for p in self._profiles_with("cost")]
        return None

    @staticmethod
    def _basename(full):
        return full.rsplit("/", 1)[-1]

    # ---------- live update ----------
    def update_from(self, active_categories):
        live = self._live_nodes()
        self._graph_ok = live is not None
        basenames = set(self._basename(n) for n in (live or []))
        rows = []
        self.status_by_category = {}

        for cat in active_categories:
            expected = self.expected_names(cat)
            exp_count = len(expected) if expected is not None else None

            if self._graph_ok:
                # keep EVERY expected node in the list; flag whether it is up so
                # failed ones can be shown in red rather than vanishing.
                node_states = [(n, n in basenames) for n in (expected or [])]
                actual = sum(1 for _, up in node_states if up)
                if exp_count is None:
                    status = "all" if actual else "none"
                elif actual == 0:
                    status = "none"
                elif actual >= exp_count:
                    status = "all"
                else:
                    status = "partial"
                count = (actual, exp_count)
            else:
                # graph offline -> can't verify; show configured names as up
                node_states = [(n, True) for n in (expected or [])]
                status = "all"
                count = (len(node_states), exp_count)

            self.status_by_category[cat] = status
            rows.append((cat, CATEGORY_COLORS.get(cat, "#2DD4BF"), status, node_states, count))
        self._rows = rows
        self.update()

    def total_node_count(self):
        # header shows live (running) nodes only
        return sum(1 for _, _, _, states, _ in self._rows for _, up in states if up)

    # ---------- painting ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()

        card = QPainterPath()
        card.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 14, 14)
        p.fillPath(card, QBrush(_qc(_C["bg_card"])))
        p.setPen(QPen(_qc(_C["border"]), 1.2))
        p.drawPath(card)

        f_h = QFont(self.font()); f_h.setPixelSize(12); f_h.setBold(True)
        f_h.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
        p.setFont(f_h); p.setPen(QPen(_qc(_C["text"])))
        p.drawText(QRectF(self.PAD, 10, w - 2 * self.PAD, 18),
                   Qt.AlignVCenter | Qt.AlignLeft, "LAUNCH ACTIVITY")
        f_c = QFont(self.font()); f_c.setPixelSize(10); p.setFont(f_c)
        p.setPen(QPen(_qc(_C["text_faint"])))
        n = self.total_node_count()
        sub = f"{n} node" + ("" if n == 1 else "s")
        if not self._graph_ok:
            sub = "graph offline · " + sub
        p.drawText(QRectF(self.PAD, 10, w - 2 * self.PAD, 18),
                   Qt.AlignVCenter | Qt.AlignRight, sub)
        p.setPen(QPen(_qc(_C["border"]), 1.0))
        p.drawLine(QPointF(self.PAD, self.HEADER_H), QPointF(w - self.PAD, self.HEADER_H))

        if not self._rows:
            f_e = QFont(self.font()); f_e.setPixelSize(11); p.setFont(f_e)
            p.setPen(QPen(_qc(_C["text_faint"])))
            p.drawText(QRectF(self.PAD, self.HEADER_H, w - 2 * self.PAD, 60),
                       Qt.AlignHCenter | Qt.AlignTop, "\nNo nodes launched yet")
            p.end(); return

        # geometry pass
        y = self.HEADER_H + 12
        rows_geom = []
        for cat, color, status, node_states, count in self._rows:
            cat_y = y; y += self.CAT_H
            child = []
            for nm, up in node_states:
                child.append((nm, up, y + self.CHILD_H / 2)); y += self.CHILD_H
            if not node_states:                 # nothing expected / config unread
                child.append((None, False, y + self.CHILD_H / 2)); y += self.CHILD_H
            y += 6
            rows_geom.append((cat, color, status, count, cat_y, child))
        last = rows_geom[-1][5]
        spine_bottom = last[-1][2] if last else rows_geom[-1][4] + self.CAT_H / 2

        p.setPen(QPen(_qc(_C["spine"]), 2.0))
        p.drawLine(QPointF(self.SPINE_X, self.HEADER_H + 14), QPointF(self.SPINE_X, spine_bottom))

        f_cat = QFont(self.font()); f_cat.setPixelSize(12); f_cat.setBold(True)
        f_ch = QFont(self.font()); f_ch.setPixelSize(11)
        f_cnt = QFont(self.font()); f_cnt.setPixelSize(9)

        for cat, color, status, count, cat_y, child in rows_geom:
            cc = _qc(color)
            cy = cat_y + self.CAT_H / 2
            # category node on the spine (its own identity colour)
            p.setBrush(QBrush(_qc(color, 45))); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(self.SPINE_X, cy), 8, 8)
            p.setBrush(QBrush(cc)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(self.SPINE_X, cy), 4.5, 4.5)
            p.setFont(f_cat); p.setPen(QPen(cc))
            p.drawText(QRectF(self.SPINE_X + 14, cat_y, w - self.SPINE_X - 14 - 66, self.CAT_H),
                       Qt.AlignVCenter | Qt.AlignLeft, cat)

            # ---- health: status indicator box (far right) + m/n count ----
            sc = _qc(STATUS_COLOR[status])
            box = 13.0
            bx = w - self.PAD - box
            by = cy - box / 2
            # soft halo so the colour reads as a state lamp, not decoration
            p.setBrush(QBrush(_qc(STATUS_COLOR[status], 55))); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(bx - 2, by - 2, box + 4, box + 4), 5, 5)
            p.setBrush(QBrush(sc)); p.setPen(QPen(_qc(_C["bg_card"]), 1.0))
            p.drawRoundedRect(QRectF(bx, by, box, box), 4, 4)
            # count, muted, just left of the lamp
            actual, expected = count
            chip = f"{actual}/{expected}" if expected is not None else f"{actual}"
            p.setFont(f_cnt); p.setPen(QPen(_qc(_C["text_muted"])))
            p.drawText(QRectF(bx - 46, cat_y, 40, self.CAT_H),
                       Qt.AlignVCenter | Qt.AlignRight, chip)

            for nm, up, ch_cy in child:
                elbow_x = self.SPINE_X + 16
                line_col = color if up else STATUS_COLOR["none"]
                path = QPainterPath(); path.moveTo(self.SPINE_X, ch_cy); path.lineTo(elbow_x, ch_cy)
                p.setPen(QPen(_qc(line_col, 120), 1.4)); p.drawPath(path)
                if nm is None:
                    p.setFont(f_ch); p.setPen(QPen(_qc(_C["text_faint"])))
                    p.drawText(QRectF(elbow_x + 10, ch_cy - self.CHILD_H / 2,
                                      w - elbow_x - 14, self.CHILD_H),
                               Qt.AlignVCenter | Qt.AlignLeft, "no nodes detected")
                    continue
                if up:
                    # running node: filled identity-colour dot + muted name
                    p.setBrush(QBrush(_qc(color, 230))); p.setPen(Qt.NoPen)
                    p.drawEllipse(QPointF(elbow_x, ch_cy), 3.0, 3.0)
                    p.setFont(f_ch); p.setPen(QPen(_qc(_C["text_muted"])))
                    p.drawText(QRectF(elbow_x + 10, ch_cy - self.CHILD_H / 2,
                                      w - elbow_x - 30, self.CHILD_H),
                               Qt.AlignVCenter | Qt.AlignLeft, str(nm))
                else:
                    # failed node: hollow red ring + red name + small "×"
                    rc = _qc(STATUS_COLOR["none"])
                    p.setBrush(Qt.NoBrush); p.setPen(QPen(rc, 1.6))
                    p.drawEllipse(QPointF(elbow_x, ch_cy), 3.2, 3.2)
                    p.setFont(f_ch); p.setPen(QPen(rc))
                    p.drawText(QRectF(elbow_x + 10, ch_cy - self.CHILD_H / 2,
                                      w - elbow_x - 30, self.CHILD_H),
                               Qt.AlignVCenter | Qt.AlignLeft, str(nm))
                    p.drawText(QRectF(w - self.PAD - 16, ch_cy - self.CHILD_H / 2,
                                      16, self.CHILD_H),
                               Qt.AlignVCenter | Qt.AlignRight, "\u2715")
        p.end()
