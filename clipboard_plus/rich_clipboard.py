"""Self-contained rich clipboard content with plain text/image fallbacks."""

import base64
from html import escape

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QImage


def image_text_mime(text: str, image: QImage, png_data: bytes) -> QMimeData:
    encoded = base64.b64encode(png_data).decode("ascii")
    # Escape user text before embedding it in HTML; preserve line breaks.
    markup = escape(text.replace("\r\n", "\n").replace("\r", "\n")).replace("\n", "<br />")
    mime = QMimeData()
    mime.setHtml(
        '<html><head><meta charset="utf-8"></head><body>'
        '<!--StartFragment--><div style="white-space: pre-wrap;">%s</div>'
        '<div><img src="data:image/png;base64,%s" width="%d" height="%d" /></div>'
        '<!--EndFragment--></body></html>'
        % (markup, encoded, image.width(), image.height())
    )
    mime.setText(text)
    mime.setImageData(image)
    return mime
