from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/' # Yüklenen dosyaların kaydedileceği klasör
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'} # İzin verilen dosya uzantıları

# 'uploads' klasörünü oluştur (eğer yoksa)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    """Dosya uzantısının izin verilenler listesinde olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    """Ana sayfa - Karşılama, giriş ve kayıt seçeneklerini gösterir."""
    return render_template('index.html') # Yeni oluşturacağımız HTML dosyasını döndür

# Eski CV yükleme rotasını da koruyalım, şimdilik erişilemez olsa da
@app.route('/upload_cv_page') # Bu sayfaya ileride bir link ekleyebiliriz
def upload_cv_page():
    return render_template('upload_cv.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """CV yükleme işlemini gerçekleştirir."""
    if 'file' not in request.files:
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return "CV'niz başarıyla yüklendi! Şimdilik sadece bu mesaj var, yakında daha fazlası gelecek."
    else:
        return "Geçersiz dosya formatı. Lütfen PDF, DOC veya DOCX formatında bir dosya yükleyin."
@app.route('/register') # Yeni kayıt sayfası rotası
def register():
    """Kullanıcı kayıt formunu gösterir."""
    return render_template('register.html') # Yeni oluşturacağımız HTML dosyasını döndür

@app.route('/register_post', methods=['POST']) # Kayıt formundan gelen verileri işleyecek rota
def register_post():
    """Kayıt formundan gelen verileri alır ve işler."""
    # Form verilerine request.form ile erişebilirsiniz
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']

    # Şimdilik sadece bu bilgileri konsola yazdıralım
    # Gerçek bir uygulamada bu bilgileri veritabanına kaydetmeniz gerekir.
    print(f"Yeni Kullanıcı Kaydı:")
    print(f"İsim: {first_name}")
    print(f"Soyisim: {last_name}")
    print(f"Email: {email}")
    print(f"Şifre (Hashlenmeden Önce): {password}") # Şifreleri doğrudan saklamayın, mutlaka hashleyin!

    # Kayıt başarılı olduktan sonra kullanıcıyı bir sayfaya yönlendirebiliriz
    # Örneğin, ana sayfaya veya bir başarı mesajı sayfasına
    return redirect(url_for('index')) # Şimdilik ana sayfaya yönlendiriyoruz

# YENİ EKLENECEK KODLAR BURADA BİTİYOR

if __name__ == '__main__':
    app.run(debug=True) # Uygulamayı hata ayıklama modunda çalıştır