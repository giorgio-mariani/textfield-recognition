from PIL.Image import Image


def compute_area(barcode):
    """Compute area of the input barcode."""
    pts = barcode.polygon
    # pts = [p1, p2, p3, p4]
    area = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def get_barcode(image: Image) -> str | None:
    from pyzbar.pyzbar import decode

    bars = decode(image)
    bar = None
    if len(bars) == 0:
        return None

    # Pick barcode with
    _, bar = max([(compute_area(b), b) for b in bars])
    return bar.data.decode("utf-8")
