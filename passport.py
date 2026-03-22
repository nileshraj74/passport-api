from flask import Flask, request, render_template, send_file, jsonify
from flask_cors import CORS  # ✅ NEW
from PIL import Image, ImageOps, ImageEnhance
from io import BytesIO
from rembg import remove, new_session
import cv2
import numpy as np
import os
import sys
import webbrowser

# Fix for EXE/template path
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

app = Flask(__name__, template_folder=os.path.join(base_path, "templates"))

# ✅ Enable CORS (VERY IMPORTANT for Flutter)
CORS(app)

# AI model
session = new_session("u2net_human_seg")


@app.route("/")
def index():
    return render_template("index.html")


# 🎯 Face auto-center
def auto_center_face(pil_img):
    img = np.array(pil_img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) == 0:
        return pil_img

    x, y, w, h = faces[0]

    cx = x + w // 2
    cy = y + h // 2

    crop_w = int(w * 1.8)
    crop_h = int(h * 2.4)

    start_x = max(cx - crop_w // 2, 0)
    start_y = max(cy - crop_h // 2, 0)

    end_x = min(start_x + crop_w, img.shape[1])
    end_y = min(start_y + crop_h, img.shape[0])

    cropped = img[start_y:end_y, start_x:end_x]

    return Image.fromarray(cropped)


# 🧠 Image processing pipeline
def process_single_image(input_image_bytes):
    img = Image.open(BytesIO(input_image_bytes)).convert("RGB")

    # Padding
    padding = int(max(img.size) * 0.1)
    img = ImageOps.expand(img, border=padding, fill=(255, 255, 255))

    # Convert to bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Background removal
    output_bytes = remove(buffer.read(), session=session)
    img = Image.open(BytesIO(output_bytes))

    # White background
    if img.mode in ("RGBA", "LA"):
        alpha = img.split()[-1]
        alpha = ImageEnhance.Contrast(alpha).enhance(2.0)
        alpha = alpha.point(lambda p: 255 if p > 180 else 0)

        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=alpha)
        img = bg
    else:
        img = img.convert("RGB")

    # Face center
    img = auto_center_face(img)

    # Enhance
    img = ImageEnhance.Sharpness(img).enhance(1.3)
    img = ImageEnhance.Brightness(img).enhance(1.05)

    return img


@app.route("/api/process", methods=["POST"])
def process():
    try:
        print("API HIT ✅")

        if 'image' not in request.files:
            return "No image", 400

        file = request.files['image']
        print("File received:", file.filename)

        # your existing logic...

    except Exception as e:
        print("ERROR OCCURRED:", str(e))
        return str(e), 500

def api_process():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400

    file = request.files["image"]
    copies = int(request.form.get("copies", 6))  # ✅ NEW

    try:
        img = process_single_image(file.read())

        passport_width = 413
        passport_height = 531

        img = img.resize((passport_width, passport_height), Image.LANCZOS)

        # 🧾 Create A4 layout (same as old logic)
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

        return send_file(
            output,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="passport_multiple.pdf",
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # 👈 IMPORTANT (10000)

    print(f"Server running on port {port}")

    app.run(host="0.0.0.0", port=port)
