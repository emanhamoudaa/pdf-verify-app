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

# القالب الخاص بصفحة عرض المستندات
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>ePortal - AFZ Document Verification</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f4f7f6; text-align: center; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; max-width: 600px; width: 100%; }
        input[type="text"], input[type="file"] { margin: 10px 0; padding: 10px; width: 80%; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #218838; }
        iframe { width: 100%; height: 500px; border: 1px solid #ccc; margin-top: 20px; }
        .barcode-box { margin-top: 15px; background: #fafafa; padding: 10px; border: 1px dashed #bbb; }
    </style>
</head>
<body>
    <div class="card">
        <h2>نظام التحقق من المستندات - AFZ</h2>
        <form action="/Documents" method="GET">
            <input type="text" name="drn" placeholder="أدخل رقم الـ DRN للبحث..." value="{{ current_drn }}">
            <button type="submit">بحث</button>
        </form>
        <hr>
        <h3>رفع مستند جديد</h3>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="text" name="custom_drn" placeholder="أدخل رقم DRN للمستند" required><br>
            <input type="file" name="pdf_file" accept=".pdf" required><br>
            <button type="submit" style="background-color: #007bff;">رفع واستخراج الباركود</button>
        </form>

        {% if pdf_url %}
            <h3 style="color: green; margin-top: 20px;">تم العثور على المستند!</h3>
            
            {% if barcode_url %}
                <div class="barcode-box">
                    <h4>الباركود المولد للمستند:</h4>
                    <img src="{{ barcode_url }}" alt="Document Barcode" style="max-width: 250px;">
                </div>
            {% endif %}

            <iframe src="{{ pdf_url }}"></iframe>
        {% elif current_drn %}
            <h3 style="color: red; margin-top: 20px;">لم يتم العثور على مستند بهذا الرقم.</h3>
        {% endif %}
    </div>
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
        # 1. جلب رابط الـ PDF
        try:
            pdf_result = cloudinary.api.resource(f"pdfs/{drn}", resource_type="raw")
            pdf_url = pdf_result.get('secure_url')
        except Exception:
            pdf_url = None

        # 2. جلب رابط الباركود
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
            # 1. قراءة محتوى الملف بالكامل في الذاكرة
            file_bytes = file.read()

            # 2. قراءة النص من الـ PDF
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            extracted_text = ""
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n"

            # 3. توليد الباركود برقم الـ DRN
            code128 = barcode.get_barcode_class('code128')
            rv = io.BytesIO()
            code = code128(custom_drn, writer=ImageWriter())
            code.write(rv)
            rv.seek(0)

            # 4. رفع ملف الـ PDF إلى Cloudinary
            cloudinary.uploader.upload(
                io.BytesIO(file_bytes),
                public_id=f"pdfs/{custom_drn}",
                resource_type="raw"
            )

            # 5. رفع صورة الباركود إلى Cloudinary
            cloudinary.uploader.upload(
                rv,
                public_id=f"barcodes/{custom_drn}",
                resource_type="image"
            )

        except Exception as e:
            print(f"Error during upload: {e}")

        return redirect(url_for('documents', drn=custom_drn))
    
    return redirect(url_for('documents'))

if __name__ == '__main__':
    app.run(debug=True)
