from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageOps, ImageEnhance
from io import BytesIO
import os

app = Flask(__name__)
CORS(app)

# ✅ Home route
@app.route("/")
def home():
    return "Passport API is running ✅"


# 🎯 Simple image processing (NO rembg)
def process_single_image(input_bytes):
    img = Image.open(BytesIO(input_bytes)).convert("RGB")

    # Padding
    padding = int(max(img.size) * 0.1)
    img = ImageOps.expand(img, border=padding, fill=(255, 255, 255))

    # Enhance
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageEnhance.Brightness(img).enhance(1.05)

    return img


# ✅ MAIN API
@app.route("/api/process", methods=["POST"])
def process():
    try:
        print("API HIT ✅")

        if "image" not in request.files:
            return "No image uploaded", 400

        file = request.files["image"]
        print("File received:", file.filename)

        copies = int(request.form.get("copies", 6))

        # Process image
        img = process_single_image(file.read())

        passport_width = 413
        passport_height = 531

        img = img.resize((passport_width, passport_height), Image.LANCZOS)

        # 🧾 A4 layout
        border = 2
        spacing = 10
        margin_x, margin_y = 20, 20
        a4_w, a4_h = 2480, 3508

        img = ImageOps.expand(img, border=border, fill="black")

        paste_w = passport_width + 2 * border
        paste_h = passport_height + 2 * border

        page = Image.new("RGB", (a4_w, a4_h), "white")

        cols = (a4_w - margin_x) // (paste_w + spacing)
        rows = (a4_h - margin_y) // (paste_h + spacing)

        count = 0

        for r in range(rows):
            for c in range(cols):
                if count >= copies:
                    break

                x = margin_x + c * (paste_w + spacing)
                y = margin_y + r * (paste_h + spacing)

                page.paste(img, (x, y))
                count += 1

            if count >= copies:
                break

        output = BytesIO()
        page.save(output, format="PDF", dpi=(300, 300))
        output.seek(0)

        print("PDF generated ✅")

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="passport.pdf",
        )

    except Exception as e:
        print("ERROR:", str(e))
        return str(e), 500


# ✅ Run app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
