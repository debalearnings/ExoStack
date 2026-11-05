import os, math
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF

app = QApplication([])
ACCENT = "#2DD4BF"
MUTED  = "#AEB9C7"

def save_refresh(path, color=ACCENT, S=128):
    pm = QPixmap(S, S); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    cx, cy = S / 2, S / 2
    r  = S * 0.30                  # circle radius
    sw = S * 0.072                 # stroke width

    # --- Arc: leave a gap at the tip end so the arrowhead has clear space ---
    ah_len  = S * 0.22             # arrowhead length along the tangent
    ah_half = S * 0.15             # half-width of the arrowhead base

    start_deg = 55.0               # where the arc starts (math degrees, CCW from 3-o'clock)
    end_deg   = start_deg + 270.0  # end of arc before arrowhead gap

    # Draw the arc
    pen = QPen(QColor(color), sw, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen); p.setBrush(Qt.NoBrush)
    # Qt drawArc: startAngle in 1/16 deg, CCW → appears CW on screen (y-down)
    p.drawArc(QRectF(cx - r, cy - r, 2*r, 2*r),
              int(start_deg * 16), int(270.0 * 16))

    # --- Arrowhead positioned at the tip of the arc (end_deg) ---
    # Position on the arc (Qt coord: x right, y down)
    er = math.radians(end_deg)
    tip_x = cx + r * math.cos(er)
    tip_y = cy - r * math.sin(er)   # y-flip

    # Tangent direction at end_deg for a CCW (math) arc, displayed CW:
    #   d/dθ of (cos θ, -sin θ) = (-sin θ, -cos θ)
    tx = -math.sin(er)
    ty = -math.cos(er)

    # Perpendicular (points inward/outward from circle)
    px, py = -ty, tx

    # Arrowhead vertices: tip extended forward, two base corners spread wide
    tip  = QPointF(tip_x + tx * sw * 0.4,
                   tip_y + ty * sw * 0.4)
    base_x = tip_x - tx * ah_len
    base_y = tip_y - ty * ah_len
    left  = QPointF(base_x + px * ah_half, base_y + py * ah_half)
    right = QPointF(base_x - px * ah_half, base_y - py * ah_half)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPolygon(QPolygonF([tip, left, right]))
    p.end()
    pm.save(path, "PNG")
    print("saved", path)

def save_chevron(path, color=MUTED, S=64):
    pm = QPixmap(S, S); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color), S * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    w = S * 0.30; cx, cy = S / 2, S / 2 + S * 0.04
    p.drawLine(QPointF(cx - w, cy - w * 0.55), QPointF(cx, cy + w * 0.55))
    p.drawLine(QPointF(cx, cy + w * 0.55), QPointF(cx + w, cy - w * 0.55))
    p.end(); pm.save(path, "PNG"); print("saved", path)

os.makedirs("resources", exist_ok=True)
save_refresh("resources/icon_refresh.png", ACCENT, 128)
save_refresh("resources/REFRESH_BUTTON.jpg", ACCENT, 128)
save_chevron("resources/chevron_down.png", MUTED, 64)
save_chevron("resources/chevron_down_accent.png", ACCENT, 64)
print("done")
