import os
import requests
from PIL import Image, ImageDraw, ImageFont

# Category -> gradient color pairs for branded visual placeholders
CATEGORY_COLORS = {
    "Developer Technology": [(30, 60, 114), (42, 82, 152)],
    "AI Technology":        [(76, 36, 130), (142, 68, 173)],
    "Comparison Articles":  [(22, 80, 100), (34, 139, 140)],
    "Placement Roadmaps":   [(44, 62, 80), (52, 92, 125)],
    "Resume Writing":       [(85, 98, 112), (128, 142, 155)],
    "Job Role and Career Trends": [(40, 60, 90), (70, 100, 140)],
}

class ImageClient:
    """
    Image generation client supporting both:
    1. A stub mode that generates category-branded gradient WebP placeholders with Pillow.
    2. A real API mode that calls the senior's image generation endpoint.
    """
    def __init__(self, api_url: str = "", api_key: str = ""):
        self.api_url = api_url or os.getenv("IMAGE_API_URL", "")
        self.api_key = api_key or os.getenv("IMAGE_API_KEY", "")
        self.stub_mode = not bool(self.api_url)

    def generate(
        self,
        prompt: str,
        style: str,
        slug: str,
        index: int,
        category: str = "",
        output_dir: str = "",
        width: int = 1200,
        height: int = 675
    ) -> str:
        """
        Generates an image and returns its relative path from the output root:
        e.g. "images/{slug}/section-{index}.webp" or "images/{slug}/thumbnail.webp"
        """
        if not output_dir:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(project_root, "output", "images")

        img_dir = os.path.join(output_dir, slug)
        os.makedirs(img_dir, exist_ok=True)

        filename = "thumbnail.webp" if index == 0 else f"section-{index}.webp"
        filepath = os.path.join(img_dir, filename)

        if self.stub_mode:
            self._generate_stub(filepath, prompt, style, category, width, height)
        else:
            self._call_real_api(filepath, prompt, style, width, height)

        return f"images/{slug}/{filename}"

    def _generate_stub(
        self,
        filepath: str,
        prompt: str,
        style: str,
        category: str,
        width: int,
        height: int
    ):
        """Generates a high-quality category-themed gradient placeholder using Pillow."""
        colors = CATEGORY_COLORS.get(category, [(30, 60, 114), (42, 82, 152)])
        c1, c2 = colors

        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Draw smooth vertical gradient
        for y in range(height):
            ratio = y / height
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Modern tech grid overlay
        grid_spacing = 50
        grid_color = (min(255, c2[0] + 25), min(255, c2[1] + 25), min(255, c2[2] + 25))
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Style badge
        badge_x, badge_y = 60, 60
        badge_w, badge_h = 240, 48
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
            radius=8,
            fill=(255, 255, 255, 25),
            outline=(255, 255, 255, 100),
            width=1
        )

        try:
            font_badge = ImageFont.truetype("arial.ttf", 20)
            font_title = ImageFont.truetype("arial.ttf", 36)
            font_prompt = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            font_badge = font_title = font_prompt = font_small = ImageFont.load_default()

        style_label = style.replace("_", " ").upper()
        draw.text((badge_x + 18, badge_y + 14), f"AI • {style_label}", fill=(255, 255, 255), font=font_badge)

        if category:
            draw.text((60, 130), category.upper(), fill=(180, 210, 255), font=font_small)

        # Format prompt preview
        prompt_clean = prompt.replace("\n", " ").strip()
        words = prompt_clean.split()
        line1 = " ".join(words[:12])
        line2 = " ".join(words[12:24]) + ("..." if len(words) > 24 else "")

        draw.text((60, 240), line1, fill=(255, 255, 255), font=font_title)
        if line2:
            draw.text((60, 290), line2, fill=(220, 230, 245), font=font_title)

        # Footer watermark
        draw.text((60, height - 70), "Placeholder Visual — Pending Senior Image API Deployment", fill=(170, 190, 220), font=font_prompt)
        draw.text((width - 240, height - 60), "BlogGraph-AI Image Client", fill=(140, 160, 190), font=font_small)

        img.save(filepath, "WEBP", quality=90)
        print(f"[ImageClient Stub] Saved placeholder: {filepath}")

    def _call_real_api(
        self,
        filepath: str,
        prompt: str,
        style: str,
        width: int,
        height: int
    ):
        """Calls the actual image generation API and writes the returned image bytes."""
        payload = {
            "prompt": prompt,
            "style": style,
            "width": width,
            "height": height,
            "format": "webp"
        }
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            print(f"[ImageClient API] Calling {self.api_url} with style '{style}'...")
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"[ImageClient API] Saved live image: {filepath}")
        except Exception as e:
            print(f"[ImageClient API] Live API request failed ({e}). Falling back to stub.")
            self._generate_stub(filepath, prompt, style, "", width, height)
