"""Color contrast shared by SVG preparation; independent of video rendering."""


def contrast(a, b):
    """WCAG contrast for solid sRGB text/background pairs."""

    def luminance(color):
        channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            n / 12.92 if n <= 0.04045 else ((n + 0.055) / 1.055) ** 2.4
            for n in channels
        ]
        return sum(n * w for n, w in zip(linear, (0.2126, 0.7152, 0.0722)))

    x, y = sorted((luminance(a), luminance(b)))
    return (y + 0.05) / (x + 0.05)
