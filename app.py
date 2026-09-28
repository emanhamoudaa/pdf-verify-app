import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response
import cloudinary
import cloudinary.uploader
import cloudinary.api
import io
from pypdf import PdfReader
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# إعدادات Cloudinary الخاصة بكِ
cloudinary.config( 
  cloud_name = "vdzxisy2", 
  api_key = "873658453387589", 
  api_secret = "a9BPwsKjpp1oCl-hNDrWv-w_boM",
  secure = True
)

# مجلد حفظ واستعراض ملفات الـ PDF
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# تصميم HTML/CSS مطابق تماماً للواجهة التي بالصورة
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FZA - Verify Document</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }
        body {
            background-color: #eef1f5;
            padding: 20px;
        }
        .main-container {
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        /* الشريط العلوي */
        .header-bar {
            background-color: #1a1a1a;
            color: #ffffff;
            padding: 12px 20px;
            font-size: 18px;
            font-weight: bold;
        }
        /* منطقة البحث */
        .search-section {
            padding: 20px;
            background-color: #ffffff;
        }
        .input-label {
            display: block;
            color: #888888;
            font-size: 14px;
            margin-bottom: 8px;
        }
        .drn-input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 3px;
            font-size: 15px;
            color: #555555;
            margin-bottom: 15px;
            outline: none;
        }
        /* الأزرار */
        .buttons-row {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .btn-search {
            flex: 2;
            background-color: #1a1a1a;
            color: white;
            padding: 10px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            text-align: center;
        }
        .btn-download {
            flex: 1;
            background-color: #1a1a1a;
            color: white;
            padding: 10px;
            border: none;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            text-align: center;
            text-decoration: none;
        }
        .btn-search:hover, .btn-download:hover {
            background-color: #333333;
        }
        /* منطقة عرض المستند */
        .pdf-viewer-container {
            width: 100%;
            height: 800px;
            border: 1px solid #ccc;
            background-color: #525659;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .no-doc {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: #ffffff;
            font-size: 18px;
        }
        /* نمط رفع ملف جديد للتجربة */
        .upload-box {
            background: #f8f9fa;
            border: 1px dashed #ccc;
            padding: 15px;
            margin-bottom: 15px;
            text-align: center;
        }
    </style>
</head>
<body>

<div class="main-container">
    <!-- الشريط العلوي -->
    <div class="header-bar">
        Verify Document
    </div>

    <div class="search-section">
        <!-- نموذج البحث عبر الـ DRN -->
        <form method="GET" action="/Documents">
            <label class="input-label">Enter Document Number</label>
            <input type="text" name="drn" class="drn-input" value="{{ current_drn }}" placeholder="e.g. 7558fa20-345a-47a9-8e03-b9e9708c5ee9">
            
            <div class="buttons-row">
                <button type="submit" class="btn-search">Search</button>
                {% if pdf_exists %}
                    <a href="/download/{{ current_drn }}" class="btn-download">Download</a>
                {% else %}
                    <button type="button" class="btn-download" style="opacity: 0.5; cursor: not-allowed;">Download</button>
                {% endif %}
            </div>
        </form>

        <!-- رفع ملف جديد برقم DRN محدد -->
        <div class="upload-box">
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <label style="font-size: 13px; font-weight: bold;">[أدوات الإدارة] رفع مستند PDF جديد ورابطه بـ DRN:</label><br><br>
                <input type="text" name="custom_drn" placeholder="أدخل رقم الـ DRN للمستند" required style="padding: 5px; width: 250px;">
                <input type="file" name="pdf_file" accept=".pdf" required style="padding: 5px;">
                <button type="submit" style="padding: 6px 15px; background: #28a745; color: white; border: none; cursor: pointer;">رفع وحفظ</button>
            </form>
        </div>

        <!-- عارض الـ PDF -->
        <div class="pdf-viewer-container">
            {% if pdf_exists %}
                <iframe src="/pdf_stream/{{ current_drn }}#toolbar=1"></iframe>
            {% else %}
                <div class="no-doc">
                    {% if current_drn %}
                        No document found for DRN: {{ current_drn }}
                    {% else %}
                        Please enter a Document Number or upload a PDF.
                    {% endif %}
                </div>
            {% endif %}
        </div>
    </div>
</div>

</body>
</html>
'''

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

        # 2. جلب رابط الباركود (إن وجد) بشكل منفصل حتى لا يتعطل عرض الـ PDF
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
        # 1. قراءة محتوى ملف الـ PDF
        pdf_reader = PdfReader(file)
        extracted_text = ""
        for page in pdf_reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

        # 2. تحديد البيانات المراد تحويلها لباركود 
        # (يمكنك استخدام كامل النص أو أول 100 حرف أو رقم الـ DRN نفسه)
        barcode_data = custom_drn # أو extracted_text[:100] إذا أردتِ قراءة جزء من نص الـ PDF

        # 3. توليد صورة الباركود في الذاكرة (Code128)
        code128 = barcode.get_barcode_class('code128')
        rv = io.BytesIO()
        code = code128(barcode_data, writer=ImageWriter())
        code.write(rv)
        rv.seek(0)

        # 4. إعادة إرجاع مؤشر ملف الـ PDF لأوله لرفعه
        file.seek(0)

        # 5. رفع ملف الـ PDF إلى Cloudinary
        cloudinary.uploader.upload(
            file,
            public_id=f"pdfs/{custom_drn}",
            resource_type="raw"
        )

        # 6. رفع صورة الباركود المنشأة إلى Cloudinary بنفس رقم الـ DRN
        cloudinary.uploader.upload(
            rv,
            public_id=f"barcodes/{custom_drn}",
            resource_type="image"
        )

        return redirect(url_for('documents', drn=custom_drn))
    
    return redirect(url_for('documents'))

@app.route('/pdf_stream/<drn>')
def pdf_stream(drn):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{drn}.pdf")
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='application/pdf')
    return "File Not Found", 404

@app.route('/download/<drn>')
def download_pdf(drn):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{drn}.pdf")
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=f"Document_{drn}.pdf")
    return "File Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
