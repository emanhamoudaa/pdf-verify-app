import os
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response
import cloudinary
import cloudinary.uploader
import cloudinary.api

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# 1. إعدادات Cloudinary (استبدلي القيم ببيانات حسابك)
cloudinary.config( 
  cloud_name = "vdzxisy2", 
  api_key = "873658453387589", 
  api_secret = "a9BPwsKjpp1oCl-hNDrWv-w_boM",
  secure = True
)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FZA - Verify Document</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, sans-serif; }
        body { background-color: #eef1f5; padding: 20px; }
        .main-container { max-width: 1200px; margin: 0 auto; background: #ffffff; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header-bar { background-color: #1a1a1a; color: #ffffff; padding: 12px 20px; font-size: 18px; font-weight: bold; }
        .search-section { padding: 20px; background-color: #ffffff; }
        .input-label { display: block; color: #888888; font-size: 14px; margin-bottom: 8px; }
        .drn-input { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 3px; font-size: 15px; color: #555555; margin-bottom: 15px; outline: none; }
        .buttons-row { display: flex; gap: 10px; margin-bottom: 20px; }
        .btn-search { flex: 2; background-color: #1a1a1a; color: white; padding: 10px; border: none; cursor: pointer; font-weight: bold; font-size: 14px; text-align: center; }
        .btn-download { flex: 1; background-color: #1a1a1a; color: white; padding: 10px; border: none; cursor: pointer; font-weight: bold; font-size: 14px; text-align: center; text-decoration: none; }
        .btn-search:hover, .btn-download:hover { background-color: #333333; }
        .pdf-viewer-container { width: 100%; height: 800px; border: 1px solid #ccc; background-color: #525659; }
        iframe { width: 100%; height: 100%; border: none; }
        .no-doc { display: flex; justify-content: center; align-items: center; height: 100%; color: #ffffff; font-size: 18px; }
        .upload-box { background: #f8f9fa; border: 1px dashed #ccc; padding: 15px; margin-bottom: 15px; text-align: center; }
    </style>
</head>
<body>

<div class="main-container">
    <div class="header-bar">Verify Document</div>
    <div class="search-section">
        <form method="GET" action="/Documents">
            <label class="input-label">Enter Document Number</label>
            <input type="text" name="drn" class="drn-input" value="{{ current_drn }}" placeholder="e.g. 7558fa20-345a-47a9-8e03-b9e9708c5ee9">
            <div class="buttons-row">
                <button type="submit" class="btn-search">Search</button>
                {% if pdf_url %}
                    <a href="{{ pdf_url }}" download class="btn-download" target="_blank">Download</a>
                {% else %}
                    <button type="button" class="btn-download" style="opacity: 0.5; cursor: not-allowed;">Download</button>
                {% endif %}
            </div>
        </form>

        <div class="upload-box">
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <label style="font-size: 13px; font-weight: bold;">[أدوات الإدارة] رفع مستند PDF جديد ورابطه بـ DRN:</label><br><br>
                <input type="text" name="custom_drn" placeholder="أدخل رقم الـ DRN للمستند" required style="padding: 5px; width: 250px;">
                <input type="file" name="pdf_file" accept=".pdf" required style="padding: 5px;">
                <button type="submit" style="padding: 6px 15px; background: #28a745; color: white; border: none; cursor: pointer;">رفع وحفظ سحابياً</button>
            </form>
        </div>

        <div class="pdf-viewer-container">
            {% if pdf_url %}
                <iframe src="{{ pdf_url }}#toolbar=1"></iframe>
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
  
@app.route('/upload', methods=['POST'])
def upload_file():
    custom_drn = request.form.get('custom_drn', '').strip()
    file = request.files.get('pdf_file')

    if custom_drn and file:
        # رفع الملف إلى Cloudinary
        cloudinary.uploader.upload(
            file,
            public_id=f"pdfs/{custom_drn}.pdf",
            resource_type="raw"
        )
        return redirect(url_for('documents', drn=custom_drn))
    
    return redirect(url_for('documents'))
@app.route('/pdf_proxy/<drn>')
def pdf_proxy(drn):
    url = None
    # 1. المحاولة الأولى: البحث برقم الـ DRN مع امتداد .pdf
    try:
        res_info = cloudinary.api.resource(f"pdfs/{drn}.pdf", resource_type="raw")
        url = res_info.get('secure_url')
    except Exception:
        # 2. المحاولة الثانية: البحث برقم الـ DRN بدون امتداد (للملفات المرفوعة سابقاً)
        try:
            res_info = cloudinary.api.resource(f"pdfs/{drn}", resource_type="raw")
            url = res_info.get('secure_url')
        except Exception:
            url = None

    if not url:
        return "Document Not Found", 404

    # جلب محتوى الملف من Cloudinary وتمريره للمتصفح كـ PDF مباشرة
    res = requests.get(url)
    response = Response(res.content, content_type='application/pdf')
    response.headers['Content-Disposition'] = f'inline; filename="{drn}.pdf"'
    return response


@app.route('/')
@app.route('/Documents')
def documents():
    drn = request.args.get('drn', '').strip()
    pdf_url = None

    if drn:
        # استخدام الـ Proxy الداخلي لعرض الملف دائماً بداخل الـ iframe
        pdf_url = url_for('pdf_proxy', drn=drn)

    return render_template_string(HTML_TEMPLATE, current_drn=drn, pdf_url=pdf_url)
