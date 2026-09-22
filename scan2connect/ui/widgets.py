from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QLabel

VIEWFINDER_COLOR = QColor(255, 255, 255, 180)
HIGHLIGHT_COLOR = QColor(76, 175, 80)


class CameraView(QLabel):
    """Displays camera frames with a QR highlight overlay and an idle viewfinder guide.

    The base pixmap is painted first, then either the last detected QR
    code's corners (scaled from frame space into the pixmap's displayed
    rect) or, when nothing is currently highlighted, a centered
    viewfinder square to guide framing.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._frame_size = None
        self._corners = None

    def set_frame(self, pixmap, frame_size):
        """Set the frame to display and the (width, height) it was captured at."""
        self._frame_size = frame_size
        self.setPixmap(pixmap)

    def set_highlight(self, corners):
        """Set the QR corner points (frame-space, Nx2) to highlight, or None to clear."""
        self._corners = corners
        self.update()

    def clear_highlight(self):
        self.set_highlight(None)

    def clear(self):
        super().clear()
        self._frame_size = None
        self._corners = None

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            self._draw_viewfinder(painter, self.rect())
            painter.end()
            return

        displayed_rect = self._displayed_pixmap_rect(pixmap)

        if self._corners is not None and self._frame_size:
            self._draw_highlight(painter, displayed_rect)
        else:
            self._draw_viewfinder(painter, displayed_rect)

        painter.end()

    def _displayed_pixmap_rect(self, pixmap):
        """Return the rect the scaled, centered pixmap actually occupies within this widget."""
        widget_size = self.size()
        scaled = pixmap.size().scaled(widget_size, Qt.KeepAspectRatio)
        x = (widget_size.width() - scaled.width()) / 2
        y = (widget_size.height() - scaled.height()) / 2
        return QRectF(x, y, scaled.width(), scaled.height())

    def _draw_highlight(self, painter, displayed_rect):
        frame_w, frame_h = self._frame_size
        if frame_w <= 0 or frame_h <= 0:
            return

        scale_x = displayed_rect.width() / frame_w
        scale_y = displayed_rect.height() / frame_h

        polygon = QPolygonF(
            [
                QPointF(
                    displayed_rect.x() + x * scale_x,
                    displayed_rect.y() + y * scale_y,
                )
                for x, y in self._corners
            ]
        )

        pen = QPen(HIGHLIGHT_COLOR, 3)
        painter.setPen(pen)
        painter.setBrush(QColor(76, 175, 80, 40))
        painter.drawPolygon(polygon)

    def _draw_viewfinder(self, painter, displayed_rect):
        side = min(displayed_rect.width(), displayed_rect.height()) * 0.6
        if side <= 0:
            return

        center = displayed_rect.center()
        guide_rect = QRectF(0, 0, side, side)
        guide_rect.moveCenter(center)

        pen = QPen(VIEWFINDER_COLOR, 2, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(guide_rect, 12, 12)
