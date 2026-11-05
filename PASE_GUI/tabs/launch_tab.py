"""
Launch tab — "Sensing → Actuation" control loop.

The seven launch node widgets are unchanged; this tab only (a) repositions
them around a loop in their order of operation, (b) paints a progressive
LED ring + connective leads + a central wearable-device emblem behind them,
and (c) polls each node's existing running flag (read-only) to light the
ring as nodes come online. No node logic is touched.
"""

import math
import os
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QPainterPath, QPixmap
)

from widgets.hub_connections import HubConnections
from widgets.synchronizer import Synchronizer
from widgets.gaitdetection import GaitEventDetector
from widgets.motionplanner import MotionPlanner
from widgets.profilemanager import ProfileManager
from widgets.hiloptimizer import HILOptimization
from widgets.costcomputation import CostComputation
from widgets.launch_activity_tree import LaunchActivityTree

try:
    from theme import COLORS
except Exception:
    COLORS = {
        "bg_0": "#0F141A", "bg_1": "#161D26", "bg_2": "#1C2530", "bg_3": "#232E3B",
        "border": "#2A3543", "border_strong": "#3A4A5E", "text": "#E8EEF4",
        "text_muted": "#94A2B3", "text_faint": "#5E6E80", "accent": "#2DD4BF",
        "accent_hi": "#54E8D6", "accent_dim": "#15786E", "success": "#34D399",
        "warning": "#F4B14C", "danger": "#F2706B",
    }


def _qc(hexstr, a=255):
    c = QColor(hexstr)
    c.setAlpha(a)
    return c


class LaunchTab(QWidget):
    def __init__(self, signal_bus):
        super().__init__()
        self.signal_bus = signal_bus
        self.setObjectName("launchTab")

        # --- the seven node widgets (unchanged), in order of operation ---
        self.hub_box = HubConnections(title="HUB CONNECTIONS", parent=self)
        self.sync_box = Synchronizer(title="SYNCHRONIZER", parent=self)
        self.event_box = GaitEventDetector(title="GAIT DETECTION", parent=self)
        self.mplanner_box = MotionPlanner(title="MOTION PLANNING", parent=self)
        self.profile_box = ProfileManager(title="PROFILE MANAGER", parent=self)
        self.hil_box = HILOptimization(title="HIL OPTIMIZER", parent=self)
        self.cost_box = CostComputation(title="COST COMPUTATION", parent=self)

        # (widget, short label, running-state getter) — read-only state polling
        self.nodes = [
            (self.hub_box,      "HUB",     lambda: getattr(self.hub_box, "connected", False)),
            (self.sync_box,     "SYNC",    lambda: getattr(self.sync_box, "running", False)),
            (self.event_box,    "GAIT",    lambda: getattr(self.event_box, "running", False)),
            (self.mplanner_box, "PLAN",    lambda: getattr(self.mplanner_box, "running", False)),
            (self.profile_box,  "PROFILE", lambda: getattr(self.profile_box, "running", False)),
            (self.hil_box,      "HIL",     lambda: getattr(self.hil_box, "running", False)),
            (self.cost_box,     "COST",    lambda: getattr(self.cost_box, "running", False)),
        ]
        for widget, _, _ in self.nodes:
            widget.show()

        # category display names for the live activity tree (HUB excluded —
        # it's a connection, not a launched ROS node)
        self._categories = [
            None,               # hub
            "Synchronizer",
            "Gait Detection",
            "Motion Planner",
            "Profile Manager",
            "HIL Optimizer",
            "Cost Computation",
        ]
        self.tree = LaunchActivityTree(parent=self)
        self.tree.show()

        self._active = [False] * len(self.nodes)
        self._anchors = []           # (track_point, box_center) per node
        self._phase = 0.0

        # read-only poll of node running flags
        self._poll = QTimer(self)
        self._poll.timeout.connect(self._poll_states)
        self._poll.start(250)

        # gentle animation (pulse of lit elements)
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick)
        self._anim.start(45)

        self.setMinimumSize(960, 640)

    # ------------------------------------------------------------------
    def _poll_states(self):
        self._active = [bool(get()) for _, _, get in self.nodes]
        active_cats = [self._categories[i] for i, a in enumerate(self._active)
                       if a and self._categories[i]]
        self.tree.update_from(active_cats)

    def _tick(self):
        self._phase += 0.05
        self.update()

    # ------------------------------------------------------------------
    def showEvent(self, e):
        super().showEvent(e)
        self._relayout()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout()

    PANEL_W = 268   # right column reserved for the live activity tree

    def _geometry(self):
        w, h = self.width(), self.height()
        uw = max(640, w - self.PANEL_W)          # usable width for the constellation
        cx, cy = uw / 2.0, h / 2.0 + 48
        rx_o = max(230.0, uw * 0.340)
        ry_o = max(165.0, h * 0.320)
        rx_t = max(125.0, uw * 0.205)
        ry_t = max(100.0, h * 0.210)
        return w, h, cx, cy, rx_o, ry_o, rx_t, ry_t

    def _angle(self, i):
        return math.radians(-90.0 + i * (360.0 / len(self.nodes)))

    def _relayout(self):
        w, h, cx, cy, rx_o, ry_o, rx_t, ry_t = self._geometry()
        self._anchors = []
        for i, (widget, _, _) in enumerate(self.nodes):
            a = self._angle(i)
            box_cx = cx + rx_o * math.cos(a)
            box_cy = cy + ry_o * math.sin(a)
            sz = widget.size()
            bw, bh = sz.width(), sz.height()
            x = int(box_cx - bw / 2.0)
            x = max(10, min(x, (w - self.PANEL_W) - bw - 10))

            if i == 0:
                # HUB is the tallest box (250 px) and its LED sits at the top of
                # the inner ring.  Pin it to the window top so the LED is clearly
                # separate — the connector then runs from box bottom-centre down
                # to the LED, just like every other node.
                y = 14
                widget.move(x, y)
                # connector target: bottom-centre of the actual box position
                connector_tgt = QPointF(x + bw / 2.0, y + bh)
            else:
                y = max(54, min(int(box_cy - bh / 2.0), h - bh - 10))
                widget.move(x, y)
                connector_tgt = QPointF(box_cx, box_cy)

            tx = cx + rx_t * math.cos(a)
            ty = cy + ry_t * math.sin(a)
            self._anchors.append((QPointF(tx, ty), connector_tgt))

        # live activity panel on the right
        pw = self.PANEL_W - 24
        self.tree.setGeometry(w - self.PANEL_W + 12, 16, pw, h - 32)
        self.update()

    # ------------------------------------------------------------------
    def _ellipse_pt(self, cx, cy, rx, ry, ang):
        return QPointF(cx + rx * math.cos(ang), cy + ry * math.sin(ang))

    def paintEvent(self, event):
        if not self._anchors:
            self._relayout()
        w, h, cx, cy, rx_o, ry_o, rx_t, ry_t = self._geometry()
        n = len(self.nodes)
        c = COLORS
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # ---- background vignette ----
        bg = QRadialGradient(cx, cy, max(w, h) * 0.75)
        bg.setColorAt(0.0, _qc(c["bg_1"]))
        bg.setColorAt(1.0, _qc(c["bg_0"]))
        p.fillRect(self.rect(), QBrush(bg))

        pulse = 0.5 + 0.5 * math.sin(self._phase)

        # ---- base loop track (dim) ----
        track = QPainterPath()
        steps = 240
        for k in range(steps + 1):
            ang = -math.pi / 2 + 2 * math.pi * (k / steps)
            pt = self._ellipse_pt(cx, cy, rx_t, ry_t, ang)
            if k == 0:
                track.moveTo(pt)
            else:
                track.lineTo(pt)
        p.setPen(QPen(_qc(c["bg_3"], 120), 9.0))
        p.drawPath(track)
        p.setPen(QPen(_qc(c["border"], 220), 2.4))
        p.drawPath(track)

        # ---- lit arcs (between consecutive running nodes) ----
        for i in range(n):
            j = (i + 1) % n
            if self._active[i] and self._active[j]:
                a0 = self._angle(i)
                a1 = self._angle(j)
                if a1 <= a0:
                    a1 += 2 * math.pi
                seg = QPainterPath()
                ss = 26
                for k in range(ss + 1):
                    ang = a0 + (a1 - a0) * (k / ss)
                    pt = self._ellipse_pt(cx, cy, rx_t, ry_t, ang)
                    if k == 0:
                        seg.moveTo(pt)
                    else:
                        seg.lineTo(pt)
                p.setPen(QPen(_qc(c["accent"], int(60 + 40 * pulse)), 12.0))
                p.drawPath(seg)
                p.setPen(QPen(_qc(c["accent_hi"], 230), 3.2))
                p.drawPath(seg)

        # ---- center emblem ----
        self._draw_emblem(p, cx, cy, min(rx_t, ry_t) * 0.74, pulse)

        # ---- connectors + node LEDs + order badges ----
        f_badge = QFont(self.font())
        f_badge.setPixelSize(11)
        f_badge.setBold(True)

        # status -> palette keys (base colour, bright/glow colour)
        STATUS_BASE = {"all": "accent", "partial": "warning", "none": "danger"}
        STATUS_HI = {"all": "accent_hi", "partial": "warning", "none": "danger"}

        for i, (track_pt, box_c) in enumerate(self._anchors):
            active = self._active[i]
            status = None
            if active:
                status = "all" if i == 0 else \
                    self.tree.status_by_category.get(self._categories[i], "all")
            base_key = STATUS_BASE.get(status, "border_strong")
            hi_key = STATUS_HI.get(status, "accent_hi")
            col = _qc(c[base_key]) if active else _qc(c["border_strong"])
            lead = QPen(_qc(c[base_key], int(120 + 80 * pulse)) if active else _qc(c["border"], 160),
                        2.6 if active else 1.6)
            p.setPen(lead)
            p.drawLine(track_pt, box_c)

            r_led = 9.0
            if active:
                glow = QRadialGradient(track_pt, 22)
                glow.setColorAt(0.0, _qc(c[hi_key], int(150 + 60 * pulse)))
                glow.setColorAt(1.0, _qc(c[base_key], 0))
                p.setBrush(QBrush(glow))
                p.setPen(Qt.NoPen)
                p.drawEllipse(track_pt, 22, 22)
            p.setBrush(QBrush(_qc(c[hi_key]) if active else _qc(c["bg_2"])))
            p.setPen(QPen(col, 2.0))
            p.drawEllipse(track_pt, r_led, r_led)

            # order badge (1..7) toward center
            badge_c = QPointF(
                cx + (track_pt.x() - cx) * 0.80,
                cy + (track_pt.y() - cy) * 0.80,
            )
            p.setBrush(QBrush(_qc(c["bg_0"], 220)))
            p.setPen(QPen(col, 1.4))
            p.drawEllipse(badge_c, 11, 11)
            p.setPen(QPen(_qc(c[hi_key]) if active else _qc(c["text_muted"])))
            p.setFont(f_badge)
            p.drawText(QRectF(badge_c.x() - 11, badge_c.y() - 11, 22, 22),
                       Qt.AlignCenter, str(i + 1))

        # ---- center emblem already drawn; status now lives in the right panel ----

        p.end()

    # ------------------------------------------------------------------
    # Center figure. Drop an image at resources/center_emblem.png (or .jpg)
    # to replace the drawn robot/“EXOSTACK” emblem. It is fit inside the LED
    # ring; the ring LEDs and number badges are painted afterwards, on top,
    # so they always stay visible. If no image is found the vector emblem
    # below is used as a fallback.
    EMBLEM_FILES = ("center_emblem.png", "center_emblem.jpg",
                    "center_emblem.jpeg", "center_emblem.svg")

    def _emblem_pixmap(self):
        res_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
        path = next((os.path.join(res_dir, n) for n in self.EMBLEM_FILES
                     if os.path.exists(os.path.join(res_dir, n))), None)
        if path is None:
            self._emblem_pix = None
            return None
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
        if (getattr(self, "_emblem_path", None) == path
                and getattr(self, "_emblem_mtime", None) == mtime
                and getattr(self, "_emblem_pix", None) is not None):
            return self._emblem_pix
        pm = QPixmap(path)
        self._emblem_pix = None if pm.isNull() else pm
        self._emblem_path = path
        self._emblem_mtime = mtime
        return self._emblem_pix

    def _draw_emblem(self, p, cx, cy, rc, pulse):
        pm = self._emblem_pixmap()
        if pm is None:
            self._draw_emblem_vector(p, cx, cy, rc, pulse)
            return
        side = int(2 * rc)                       # fit inside the LED ring / badges
        scaled = pm.scaled(side, side, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawPixmap(int(cx - scaled.width() / 2.0),
                     int(cy - scaled.height() / 2.0), scaled)

    def _draw_emblem_vector(self, p, cx, cy, rc, pulse):
        c = COLORS
        grad = QRadialGradient(cx, cy - rc * 0.1, rc * 1.25)
        grad.setColorAt(0.0, _qc(c["bg_2"]))
        grad.setColorAt(1.0, _qc(c["bg_1"]))
        p.setBrush(QBrush(grad))
        p.setPen(QPen(_qc(c["border_strong"], 220), 1.6))
        p.drawEllipse(QPointF(cx, cy), rc, rc)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(_qc(c["accent"], 60), 1.2))
        p.drawEllipse(QPointF(cx, cy), rc * 0.86, rc * 0.86)

        any_active = any(self._active)
        line_col = _qc(c["text"], 230)
        joint_col = _qc(c["accent_hi"], int(180 + 60 * pulse)) if any_active else _qc(c["accent"], 200)
        s = rc

        p.setPen(QPen(line_col, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        head_r = 0.085 * s
        head_c = QPointF(cx, cy - 0.52 * s)
        p.drawEllipse(head_c, head_r, head_r)
        p.drawLine(QPointF(cx, cy - 0.43 * s), QPointF(cx, cy - 0.06 * s))
        hip_y = cy - 0.02 * s
        p.drawLine(QPointF(cx - 0.20 * s, hip_y), QPointF(cx + 0.20 * s, hip_y))
        for sgn in (-1, 1):
            hip = QPointF(cx + sgn * 0.20 * s, hip_y)
            knee = QPointF(cx + sgn * 0.26 * s, cy + 0.34 * s)
            ankle = QPointF(cx + sgn * 0.19 * s, cy + 0.62 * s)
            p.drawLine(hip, knee)
            p.drawLine(knee, ankle)
            p.drawLine(ankle, QPointF(cx + sgn * 0.30 * s, cy + 0.62 * s))

        for sgn in (-1, 1):
            hip = QPointF(cx + sgn * 0.20 * s, hip_y)
            p.setPen(QPen(joint_col, 2.4))
            p.setBrush(QBrush(_qc(c["bg_0"])))
            p.drawEllipse(hip, 0.075 * s, 0.075 * s)
            p.setBrush(QBrush(joint_col))
            p.setPen(Qt.NoPen)
            p.drawEllipse(hip, 0.032 * s, 0.032 * s)

        # flow arcs hinting loop direction
        p.setPen(QPen(_qc(c["accent"], 150), 2.0, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        arc_r = rc * 1.02
        rect = QRectF(cx - arc_r, cy - arc_r, 2 * arc_r, 2 * arc_r)
        p.drawArc(rect, int(40 * 16), int(60 * 16))
        p.drawArc(rect, int(220 * 16), int(60 * 16))

        f1 = QFont(self.font()); f1.setPixelSize(max(11, int(0.16 * s))); f1.setBold(True)
        f1.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(f1)
        p.setPen(QPen(_qc(c["text"])))
        p.drawText(QRectF(cx - rc, cy + 0.66 * s, 2 * rc, 0.22 * s), Qt.AlignCenter, "EXOSTACK")
        f2 = QFont(self.font()); f2.setPixelSize(max(9, int(0.075 * s)))
        p.setFont(f2)
        p.setPen(QPen(_qc(c["text_faint"])))
        p.drawText(QRectF(cx - rc, cy + 0.84 * s, 2 * rc, 0.16 * s),
                   Qt.AlignCenter, "sensing  →  actuation")
