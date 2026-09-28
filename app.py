import os
import io
import requests
from flask import Flask, render_template_string, request, redirect, url_for, flash
import cloudinary
import cloudinary.uploader
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = 'super_secret_key_123'

# =========================================================
# بيانات الاعتماد الخاصة بـ Cloudinary
# =========================================================
CLOUDINARY_CLOUD_NAME = "vdzxisy2"
CLOUDINARY_API_KEY = "873658453387589"
# ⚠️ استبدلي النص التالي بـ API Secret الحقيقي والكامل من حسابك في Cloudinary:
CLOUDINARY_API_SECRET = "a9BPwsKjpp1oCl-hNDrWv-w_boM"

# ضبط إعدادات Cloudinary
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME.strip(),
    api_key=CLOUDINARY_API_KEY.strip(),
    api_secret=CLOUDINARY_API_SECRET.strip(),
    secure=True
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ePortal - AFZ Document Verification</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; background-color: #eef1f5; text-align: center; }
        .top-bar { background-color: #f8f9fa; padding: 10px 20px; text-align: left; border-bottom: 1px solid #ddd; }
        .search-container { background-color: #212529; color: white; padding: 12px; font-weight: bold; font-size: 16px; margin-bottom: 5px; }
        .download-btn { float: right; background-color: #6c757d; color: white; padding: 6px 15px; border: none; border-radius: 3px; cursor: pointer; }
        .admin-panel { background-color: #f1f3f5; padding: 10px; margin: 10px auto; width: 90%; max-width: 900px; border: 1px solid #ced4da; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; }
        input[type="text"] { padding: 8px; width: 250px; border: 1px solid #ccc; border-radius: 3px; }
        input[type="file"] { padding: 5px; }
        .btn-green { background-color: #28a745; color: white; padding: 8px 18px; border: none; border-radius: 3px; cursor: pointer; font-weight: bold; }
        .btn-green:hover { background-color: #218838; }
        .pdf-viewer { width: 90%; height: 650px; margin: 20px auto; border: 1px solid #ccc; background: #525659; }
        .no-doc { color: #333; margin-top: 30px; font-size: 16px; font-weight: bold; }
        .alert { background-color: #f8d7da; color: #721c24; padding: 10px; margin: 10px auto; width: 85%; border-radius: 4px; font-weight: bold; }
        .success { background-color: #d4edda; color: #155724; padding: 10px; margin: 10px auto; width: 85%; border-radius: 4px; font-weight: bold; }
    </style>
</head>
<body>

    <div class="top-bar">
        <input type="text" id="top_drn" placeholder="Enter Document Number" value="{{ current_drn or '' }}" onchange="location.href='/Documents?drn='+this.value">
    </div>

    <div class="search-container">
        Search
        {% if pdf_url %}
            <a href="{{ pdf_url }}" target="_blank" class="download-btn" style="text-decoration:none;">Download</a>
        {% else %}
            <button class="download-btn" disabled>Download</button>
        {% endif %}
    </div>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="admin-panel" dir="rtl">
        <span>[أدوات الإدارة] رفع مستند PDF ورابطه بـ DRN جديد:</span>
        <form action="/upload" method="POST" enctype="multipart/form-data" style="margin:0; display:flex; gap:10px; align-items:center;">
            <input type="text" name="custom_drn" placeholder="أدخل رقم الـ DRN (مثل 123123)" required>
            <input type="file" name="pdf_file" accept=".pdf" required>
            <button type="submit" class="btn-green">رفع وحفظ</button>
        </form>
    </div>

    {% if pdf_url %}
        {% if barcode_url %}
            <div style="margin: 15px 0;">
                <img src="{{ barcode_url }}" alt="Document Barcode" style="max-width: 250px;">
            </div>
        {% endif %}
        
        <iframe class="pdf-viewer" src="{{ pdf_url }}"></iframe>
    {% elif current_drn %}
        <div class="no-doc">No document found for DRN: {{ current_drn }}</div>
    {% endif %}

</body>
</html>
"""

@app.route('/')
@app.route('/Documents')
def documents():
    drn = request.args.get('drn', '').strip()
    pdf_url = None
    barcode_url = None

    if drn:
        try:
            pdf_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/raw/upload/pdfs/{drn}.pdf"
            barcode_url = f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/barcodes/{drn}.png"

            res = requests.head(pdf_url, timeout=5)
            if res.status_code != 200:
                pdf_url = None
                barcode_url = None
        except Exception:
            pdf_url = None
            barcode_url = None

    return render_template_string(HTML_TEMPLATE, current_drn=drn, pdf_url=pdf_url, barcode_url=barcode_url)

@app.route('/upload', methods=['POST'])
def upload_file():
    custom_drn = request.form.get('custom_drn', '').strip()
    file = request.files.get('pdf_file')

    if custom_drn and file:
        try:
            file_bytes = file.read()

            # 1. إنشاء باركود Code128
            code128 = barcode.get_barcode_class('code128')
            rv = io.BytesIO()
            code = code128(custom_drn, writer=ImageWriter())
            code.write(rv)
            rv.seek(0)

            # 2. رفع الـ PDF إلى Cloudinary
            cloudinary.uploader.upload(
                file_bytes,
                public_id=f"pdfs/{custom_drn}.pdf",
                resource_type="raw",
                overwrite=True,
                invalidate=True
            )

            # 3. رفع صورة الباركود إلى Cloudinary
            cloudinary.uploader.upload(
                rv,
                public_id=f"barcodes/{custom_drn}.png",
                resource_type="image",
                overwrite=True,
                invalidate=True
            )

            flash(f"تم رفع المستند بنجاح برقم DRN: {custom_drn}", "success")

        except Exception as e:
            flash(f"حدث خطأ أثناء الرفع: {str(e)}", "alert")

        return redirect(url_for('documents', drn=custom_drn))
    
    return redirect(url_for('documents'))

if __name__ == '__main__':
    app.run(debug=True)
