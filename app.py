import os
import re
from flask import Flask, render_template_string, request, send_file, flash, redirect, url_for
import requests
from flask import Flask, render_template_string, request, redirect, url_for, Response
import cloudinary
import cloudinary.uploader
import cloudinary.api

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
@@ -184,25 +195,31 @@
@app.route('/')
@app.route('/Documents')
def documents():
    # استخراج رقم الـ DRN من رابط الصفحة (مثال: /Documents?drn=7558fa20-...)
    drn = request.args.get('drn', '').strip()
    pdf_exists = False
    pdf_url = None

    if drn:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{drn}.pdf")
        if os.path.exists(file_path):
            pdf_exists = True
        try:
            # الحصول على رابط الملف مباشرة من Cloudinary
            result = cloudinary.api.resource(f"pdfs/{drn}", resource_type="raw")
            pdf_url = result.get('secure_url')
        except Exception:
            pdf_url = None

    return render_template_string(HTML_TEMPLATE, current_drn=drn, pdf_exists=pdf_exists)
    return render_template_string(HTML_TEMPLATE, current_drn=drn, pdf_url=pdf_url)

@app.route('/upload', methods=['POST'])
def upload_file():
    custom_drn = request.form.get('custom_drn', '').strip()
    file = request.files.get('pdf_file')

    if custom_drn and file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{custom_drn}.pdf")
        file.save(file_path)
        # رفع الملف مباشرة إلى Cloudinary باستخدام الـ DRN كـ public_id
        cloudinary.uploader.upload(
            file,
            public_id=f"pdfs/{custom_drn}",
            resource_type="raw"
        )
        return redirect(url_for('documents', drn=custom_drn))

    return redirect(url_for('documents'))
@@ -222,4 +239,4 @@ def download_pdf(drn):
    return "File Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
    app.run(debug=True, use_reloader=False, port=5000)
