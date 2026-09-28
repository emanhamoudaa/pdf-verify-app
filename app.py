import os
import io
import requests
from flask import Flask, render_template_string, request, redirect, url_for
import cloudinary
import cloudinary.uploader
import cloudinary.api
from pypdf import PdfReader
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# إعدادات Cloudinary الخاصة بكِ
cloudinary.config( 
  cloud_name = "vdzxisy2", 
  api_key = "873658453387589", 
  api_secret = "a9BPWsKjpp1oC1-hNDRwv-w_boM",
  secure = True
)

# القالب المطابق تماماً للواجهة الخاصة بكِ
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
        .search-box { padding: 15px; background: #fff; border-bottom: 2px solid #ddd; }
        .admin-panel { background-color: #f1f3f5; padding: 10px; margin: 10px auto; width: 90%; max-width: 900px; border: 1px solid #ced4da; border-radius: 4px; display: flex; align-items: center; justify-content: space-between; }
        input[type="text"] { padding: 8px; width: 250px; border: 1px solid #ccc; border-radius: 3px; }
        input[type="file"] { padding: 5px; }
        .btn-green { background-color: #28a745; color: white; padding: 8px 18px; border: none; border-radius: 3px; cursor: pointer; font-weight: bold; }
        .btn-green:hover { background-color: #218838; }
        .pdf-viewer { width: 90%; height: 600px; margin: 20px auto; border: 1px solid #ccc; background: #525659; }
        .no-doc { color: #333; margin-top: 30px; font-size: 16px; }
        .barcode-section { margin: 15px 0; }
    </style>
</head>
<body>

    <div class="top-bar">
        <input type="text" id="top_drn" placeholder="Enter Document Number" value="{{ current_drn or '' }}" onchange="location.href='/Documents?drn='+this.value">
    </div>

    <div class="search-container">
        Search
        <button class="download-btn">Download</button>
    </div>

    <!-- لوحة التحكم للرفع -->
    <div class="admin-panel" dir="rtl">
        <span>[أدوات الإدارة] رفع مستند PDF ورابطه بـ DRN جديد:</span>
        <form action="/upload" method="POST" enctype="multipart/form-data" style="margin:0; display:flex; gap:10px; align-items:center;">
            <input type="text" name="custom_drn" placeholder="أدخل رقم الـ DRN للمستند" required>
            <input type="file" name="pdf_file" accept=".pdf" required>
            <button type="submit" class="btn-green">رفع وحفظ</button>
        </form>
    </div>

    <!-- عرض الباركود والمستند -->
    {% if pdf_url %}
        {% if barcode_url %}
            <div class="barcode-section">
                <h4>الباركود الخاص بالمستند:</h4>
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
        # 1. جلب رابط الـ PDF من Cloudinary
        try:
            pdf_result = cloudinary.api.resource(f"pdfs/{drn}", resource_type="raw")
            pdf_url = pdf_result.get('secure_url')
        except Exception:
            pdf_url = None

        # 2. جلب رابط الباركود بشكل منفصل
        try:
            barcode_result = cloudinary.api.resource(f"barcodes/{drn}", resource_type="image")
            barcode_url = barcode_result.get('secure_url')
        except Exception:
            barcode_url = None

    return render_template_string(HTML_TEMPLATE, current_drn=drn, pdf_url=pdf_url, barcode_url=barcode_url)

@app.route('/upload', methods=['POST'])
def upload_file():
    custom_drn = request.form.get('custom_drn', '').strip()
    file = request.files.get('pdf_file')

    if custom_drn and file:
        try:
            file_bytes = file.read()

            # قراءة النص داخل الـ PDF
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            extracted_text = ""
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

            # إنشاء صورة الباركود Code128
            code128 = barcode.get_barcode_class('code128')
            rv = io.BytesIO()
            code = code128(custom_drn, writer=ImageWriter())
            code.write(rv)
            rv.seek(0)

            # رفع الـ PDF إلى Cloudinary
            cloudinary.uploader.upload(
                io.BytesIO(file_bytes),
                public_id=f"pdfs/{custom_drn}",
                resource_type="raw"
            )

            # رفع الباركود إلى Cloudinary
            cloudinary.uploader.upload(
                rv,
                public_id=f"barcodes/{custom_drn}",
                resource_type="image"
            )

        except Exception as e:
            print(f"Error uploading: {e}")

        return redirect(url_for('documents', drn=custom_drn))
    
    return redirect(url_for('documents'))

if __name__ == '__main__':
    app.run(debug=True)
