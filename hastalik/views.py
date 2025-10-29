from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import torch
from torchvision import transforms, models
import requests, json
import requests
import unidecode
from .models import Profile, Village, Field, Alert, ChatMessage, DiseaseHistory
from .forms import FieldForm, AlertForm
import random
from datetime import timedelta
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Post
from .models import Post, Comment

from django.conf import settings


from django.conf import settings


from django.shortcuts import render
from .models import Post
from django.conf import settings
import cv2
import numpy as np
import torch


from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.db import transaction
from django.utils import timezone
from .models import Profile
import requests
from django.core.cache import cache  # ✅ performans için





from PIL import Image, ImageEnhance

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from django.db import models  # ✅ bu önemli
from torchvision import models as tv_models  # PyTorch için ayrı isim ver
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required


# ============================================================
# 🌾 1️⃣ Yapay Zekâ Modeli (Mısır Hastalığı Tahmini)
# ============================================================



model = tv_models.resnet50(weights=None)



num_ftrs = model.fc.in_features
model.fc = torch.nn.Linear(num_ftrs, 12)

state_dict = torch.load("hastalik/corn_disease_model.pth", map_location=torch.device('cpu'))
model.load_state_dict(state_dict, strict=False)
model.eval()

class_names = [
    'Blight', 'Common_Rust', 'Gray_Leaf_Spot', 'Healthy', 'Leaf_Beetle',
    'Mold', 'Northern_Leaf_Blight', 'Phosphorus_Deficiency',
    'Potassium_Deficiency', 'Red_spider', 'sticky_insect', 'yellow_striped_flea_beetle'
]

suggestions = {
    'Blight': "🌿 Yaprak yanıklığı var, mantar ilacı kullan.",
    'Common_Rust': "🟠 Pas hastalığı; yaprakta turuncu lekeler olur.",
    'Gray_Leaf_Spot': "🔵 Yaprak lekesi, nem kontrolünü artır.",
    'Healthy': "✅ Bitki sağlıklı, mevcut koşulları koru.",
    'Mold': "⚠️ Küf varsa, nemi azalt ve havalandırmayı artır.",
    'Northern_Leaf_Blight': "🟢 Kuzey yaprak yanıklığı, fungisit önerilir.",
    'Phosphorus_Deficiency': "🟣 Fosfor eksikliği, uygun gübreleme yap.",
    'Potassium_Deficiency': "🟡 Potasyum eksikliği, potasyumlu gübre kullan.",
    'Red_spider': "🔴 Kırmızı örümcek zararlısı, yaprak altlarını kontrol et.",
    'sticky_insect': "🪲 Yapışkan böcek belirtileri, biyolojik mücadele önerilir.",
    'yellow_striped_flea_beetle': "🟡 Sarı çizgili pire böceği, yaprak delikleri oluşur."
}


@login_required
def upload_and_predict(request):
    result = None
    suggestion = None

    if request.method == 'POST' and 'image' in request.FILES:
        image = request.FILES['image']
        field_id = request.POST.get('field_id')
        selected_field = Field.objects.filter(id=field_id, owner=request.user).first()

        if not selected_field:
            messages.error(request, "Geçerli bir tarla seçmelisin!")
            return redirect('upload_and_predict')

        # --- 1️⃣ Görüntüyü oku ve RGB'ye çevir
        img = Image.open(image).convert('RGB')

        # --- 2️⃣ Görüntüyü NumPy'e çevir
        img_cv = np.array(img)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        # --- 3️⃣ Gürültü temizleme (Gaussian Blur)
        img_cv = cv2.GaussianBlur(img_cv, (3, 3), 0)

        # --- 4️⃣ Işık dengesi (adaptive histogram equalization)
        lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        lab = cv2.merge((cl, a, b))
        img_cv = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # --- 5️⃣ Renk doygunluğu ve kontrastı artır
        img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        img_pil = ImageEnhance.Contrast(img_pil).enhance(1.4)
        img_pil = ImageEnhance.Color(img_pil).enhance(1.2)
        img_pil = ImageEnhance.Sharpness(img_pil).enhance(1.3)

        # --- 6️⃣ Modele uygun dönüştürme
        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet standardı
                std=[0.229, 0.224, 0.225]
            )
        ])

        img_tensor = transform(img_pil).unsqueeze(0)

        # --- 7️⃣ Model tahmini
        with torch.no_grad():
            outputs = model(img_tensor)
            _, predicted = torch.max(outputs, 1)
            result = class_names[predicted.item()]
            suggestion = suggestions.get(result, "⚠️ Bu hastalık için öneri bulunamadı.")

        # --- 8️⃣ Veritabanı kayıtları
        if result != "Healthy" and selected_field.village:
            Alert.objects.create(
                title=f"{result} tespit edildi!",
                message=f"{selected_field.village.name} köyünde '{selected_field.name}' tarlasında {result} tespit edildi. {suggestion}",
                severity='warning',
                created_by=request.user,
                related_field=selected_field,
                village=selected_field.village
            )

        if result != "Healthy":
            DiseaseHistory.objects.create(
                field=selected_field,
                detected_by=request.user,
                disease_name=result,
                suggestion=suggestion
            )

        messages.success(request, f"{selected_field.name} tarlasında {result} tespit edildi!")

    return render(request, 'upload.html', {
        'result': result,
        'suggestion': suggestion,
        'fields': request.user.fields.all()
    })


# ============================================================
# 2️⃣ Kullanıcı İşlemleri
# ============================================================

def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, "Şifreler uyuşmuyor!")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Bu kullanıcı adı zaten alınmış!")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Bu e-posta zaten kayıtlı!")
            return redirect('register')

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            profile, _ = Profile.objects.get_or_create(user=user)

            try:
                send_verification_email(profile)
                messages.info(request, "E-posta adresine doğrulama kodu gönderildi.")
                return redirect('verify_email', user_id=user.id)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f"E-posta gönderilemedi: {e}")
                return redirect('register')

    return render(request, 'register.html')

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, f"Hoş geldin, {user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Kullanıcı adı veya şifre hatalı!")
    return render(request, 'login.html')


def logout_user(request):
    logout(request)
    messages.info(request, "Çıkış yaptın.")
    return redirect('login')


@login_required
def home(request):
    return render(request, 'home.html', {'user': request.user})


# ============================================================
# 3️⃣ Tarla Yönetimi
# ============================================================

@login_required
def field_list(request):
    fields = Field.objects.filter(owner=request.user)
    fields_data = [
        {"name": f.name, "lat": f.lat, "lon": f.lon, "crop_type": f.crop_type}
        for f in fields if f.lat and f.lon
    ]
    return render(request, "field_list.html", {
        "fields": fields,
        "fields_json": json.dumps(fields_data)
    })


@login_required
def add_field(request):
    if request.method == "POST":
        form = FieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.owner = request.user
            lat, lon = field.lat, field.lon

            # 🌍 1️⃣ Köy adını bul (reverse geocoding)
            try:
                url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
                r = requests.get(url, headers={"User-Agent": "misir-asistani"}, timeout=5)
                data = r.json()
                name = (
                    data.get("address", {}).get("village")
                    or data.get("address", {}).get("town")
                    or data.get("address", {}).get("city")
                    or "Bilinmeyen"
                )
            except Exception:
                name = "Bilinmeyen"

            # 🏘️ 2️⃣ Köy kaydı oluştur veya mevcutsa getir
            village, created = Village.objects.get_or_create(name=name)

            # 🧭 3️⃣ Eğer köyün koordinatı yoksa, tarlanın konumunu köye kaydet
            if created or not village.latitude or not village.longitude:
                village.latitude = lat
                village.longitude = lon
                village.save()

            # 🌾 4️⃣ Tarlayı kaydet
            field.village = village
            field.save()

            messages.success(request, f"{field.name} adlı tarla eklendi ({village.name} köyü).")
            return redirect("field_list")
    else:
        form = FieldForm()

    # 🌍 5️⃣ Mevcut tarlaları harita için JSON formatına dönüştür
    fields = Field.objects.filter(owner=request.user)
    fields_json = json.dumps([
        {
            "id": f.id,
            "name": f.name,
            "crop_type": f.crop_type,
            "lat": f.lat,
            "lon": f.lon,
        }
        for f in fields if f.lat and f.lon
    ])

    # 🌿 6️⃣ Sayfayı render et
    return render(request, "add_field.html", {
        "form": form,
        "fields_json": fields_json
    })
@login_required
def delete_field(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)
    
    if request.method == "POST":
        field.delete()
        messages.success(request, f"{field.name} adlı tarla silindi.")
        return redirect("field_list")

    return render(request, "confirm_delete_field.html", {"field": field})


@login_required
def field_detail(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)
    history = field.disease_history.order_by('-created_at')
    return render(request, 'field_detail.html', {'field': field, 'history': history})
@login_required
def field_history(request, field_id):
    field = get_object_or_404(Field, id=field_id, owner=request.user)
    history = DiseaseHistory.objects.filter(field=field).order_by('-created_at')

    # 💊 Son hastalık için ilaç önerisi al
    advice = get_field_advice(field)

    return render(request, 'field_history.html', {
        'field': field,
        'history': history,
        'advice': advice
    })




# ============================================================
# 4️⃣ Uyarı Sistemi
# ============================================================

@login_required
def create_alert(request):
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()
            return redirect('alert_list')
    else:
        form = AlertForm()
    return render(request, 'create_alert.html', {'form': form})


@login_required
def alert_list(request):
    profile = Profile.objects.filter(user=request.user).first()
    if not profile or not profile.village:
        alerts = []
    else:
        alerts = Alert.objects.filter(village=profile.village).order_by('-created_at')
    return render(request, 'alert_list.html', {'alerts': alerts})


# ============================================================
# 5️⃣ Köy Sohbet Sistemi
# ============================================================

@login_required
def village_chat(request):
    villages = Village.objects.filter(field__owner=request.user).distinct()

    # Köylerin hava durumu listesi
    village_weather_list = []
    for v in villages:
        weather = get_weather_for_village(v)
        village_weather_list.append({
            "id": v.id,
            "name": v.name,
            "weather": weather
        })

    selected_village = None
    messages_qs = []

    village_id = request.GET.get("village_id")
    if village_id:
        selected_village = get_object_or_404(Village, id=village_id)
        messages_qs = ChatMessage.objects.filter(village=selected_village).order_by("created_at")

    # 🟢 Mesaj veya fotoğraf gönderimi
    if request.method == "POST":
        text = request.POST.get("message", "").strip()
        image = request.FILES.get("image")  # 📸 resim desteği
        v_id = request.POST.get("village_id")

        if (text or image) and v_id:
            village = get_object_or_404(Village, id=v_id)
            ChatMessage.objects.create(sender=request.user, village=village, text=text, image=image)
            return redirect(f"/chat/?village_id={village.id}")

    return render(request, "village_chat.html", {
        "villages": villages,
        "selected_village": selected_village,
        "messages": messages_qs,
        "village_weather_list": village_weather_list
    })

def get_messages(request, village_id):
    messages_qs = ChatMessage.objects.filter(village_id=village_id).order_by('created_at')
    data = [
        {
            'sender': msg.sender.username,
            'text': msg.text,
            'created_at': msg.created_at.strftime('%H:%M'),
            'image': msg.image.url if msg.image else None,  # 🖼️ EKLENDİ
        }
        for msg in messages_qs
    ]
    return JsonResponse({'messages': data})



@csrf_exempt
def add_village_if_not_exists(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "Köy adı geçersiz"}, status=400)

        village = Village.objects.filter(name__iexact=name).first()
        created = False

        if not village:
            # ✅ Köy ismine göre koordinat bul
            name_fixed = unidecode.unidecode(name)
            geocode_url = f"https://nominatim.openstreetmap.org/search?q={name_fixed},Turkey&format=json&limit=1"

            try:
                res = requests.get(geocode_url, headers={"User-Agent": "misir-asistani"}, timeout=5)
                data = res.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    city_name = data[0]["display_name"].split(",")[-3].strip()
                else:
                    lat, lon, city_name = None, None, "Karaman"
            except Exception:
                lat, lon, city_name = None, None, "Karaman"

            village = Village.objects.create(
                name=name, city=city_name, latitude=lat, longitude=lon
            )
            created = True

        return JsonResponse({
            "id": village.id,
            "name": village.name,
            "created": created,
            "lat": village.latitude,
            "lon": village.longitude,
            "city": village.city
        })

    return JsonResponse({"error": "Sadece POST isteği kabul edilir"}, status=405)
def get_weather(lat, lon):
    API_KEY = "0ad86a9112ff44589b66dfd6f6bd6ec1"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=tr"
    r = requests.get(url)
    data = r.json()

    hava = data["weather"][0]["description"].capitalize()
    sicaklik = data["main"]["temp"]
    nem = data["main"]["humidity"]
    ruzgar = data["wind"]["speed"]

    return {
        "hava": hava,
        "sicaklik": sicaklik,
        "nem": nem,
        "ruzgar": ruzgar
    }
def get_weather_for_village(village):
    API_KEY = "0ad86a9112ff44589b66dfd6f6bd6ec1"

    # 📦 1️⃣ Cache kontrolü (aynı köy için 30 dakikada bir sorgu)
    cache_key = f"weather_{village.id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    # 📍 2️⃣ Koordinat kontrolü
    if not village.latitude or not village.longitude:
        return {"temp": "-", "desc": "Konum yok"}

    lat, lon = village.latitude, village.longitude

    # 🌤️ 3️⃣ OpenWeather API isteği
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&lang=tr"

    try:
        res = requests.get(url, timeout=5)
        data = res.json()

        if data.get("cod") != 200:
            print(f"Hava verisi alınamadı: {village.name} ({data})")
            return {"temp": "-", "desc": "Veri yok"}

        weather_data = {
            "temp": round(data["main"]["temp"]),
            "desc": data["weather"][0]["description"].capitalize()
        }

        # 🧠 4️⃣ Cache’e kaydet (30 dakika)
        cache.set(cache_key, weather_data, timeout=1800)

        return weather_data

    except Exception as e:
        print(f"Hava durumu hatası ({village.name}): {e}")
        return {"temp": "-", "desc": "Veri yok"}
def verify_email(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if not code:
            messages.error(request, "Kod giriniz.")
            return redirect('verify_email', user_id=user_id)

        # brute-force koruması
        if profile.email_verification_attempts >= 5:
            messages.error(request, "Çok fazla hatalı deneme. Yeni kod isteyin.")
            return redirect('verify_email', user_id=user_id)

        # kod geçerli mi?
        if (
            profile.email_verification_code == code and
            profile.email_verification_expiry and
            profile.email_verification_expiry > timezone.now()
        ):
            profile.is_email_verified = True
            profile.email_verification_code = None
            profile.save()
            messages.success(request, "E-posta doğrulandı! Artık giriş yapabilirsiniz.")
            login(request, profile.user)
            return redirect('home')
        else:
            profile.email_verification_attempts += 1
            profile.save()
            messages.error(request, "Kod yanlış veya süresi dolmuş.")
            return redirect('verify_email', user_id=user_id)

    return render(request, 'verify_email.html', {'profile': profile})
def resend_email(request, user_id):
    profile = get_object_or_404(Profile, user_id=user_id)
    try:
        send_verification_email(profile, force=True)
        messages.info(request, "Yeni doğrulama kodu e-posta adresinize gönderildi.")
    except Exception as e:
        messages.error(request, f"E-posta gönderilemedi: {e}")
    return redirect('verify_email', user_id=user_id)
def send_verification_email(profile, force=False):
    now = timezone.now()

    # çok sık gönderimi engelle
    if profile.last_email_sent_at and (now - profile.last_email_sent_at).total_seconds() < 30 and not force:
        raise ValueError("Çok sık e-posta gönderiliyor. Lütfen biraz bekle.")

    # 6 haneli doğrulama kodu
    code = str(random.randint(100000, 999999))
    profile.email_verification_code = code
    profile.email_verification_expiry = now + timedelta(minutes=10)
    profile.email_verification_attempts = 0
    profile.last_email_sent_at = now
    profile.save()

    # e-posta gönder
    subject = "🌽 Mısır Asistanı - E-posta Doğrulama Kodu"
    message = (
        f"Merhaba {profile.user.username},\n\n"
        f"Doğrulama kodunuz: {code}\n"
        f"Bu kod 10 dakika boyunca geçerlidir.\n\n"
        f"İyi günler!\nMısır Asistanı Ekibi"
    )

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [profile.user.email])

@login_required
def feed(request):
    selected_category = request.GET.get('category')
    posts = Post.objects.all().order_by('-created_at')

    # 🔍 kategori filtreleme
    if selected_category:
        posts = posts.filter(category=selected_category)

    my_posts = Post.objects.filter(owner=request.user).order_by('-created_at')

    return render(request, 'feed.html', {
        'posts': posts,
        'my_posts': my_posts,
        'selected_category': selected_category
    })

def trade_center(request):
    """Ticaret merkezi — şimdilik sadece geçici bir sayfa"""
    return render(request, "trade_center.html")


@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        image = request.FILES.get("image")
        is_for_sale = bool(request.POST.get("is_for_sale"))
        category = request.POST.get("category", "genel")

        Post.objects.create(
            owner=request.user,
            title=title,
            description=description,
            image=image,
            is_for_sale=is_for_sale,
            category=category,
        )
        messages.success(request, "Gönderin paylaşıldı! 📸")
        return redirect("feed")
    return render(request, "create_post.html")


@require_POST
@login_required
def like_post(request):
    post_id = request.POST.get("post_id")
    post = get_object_or_404(Post, id=post_id)
    user = request.user

    if user in post.likes.all():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True

    return JsonResponse({
        "liked": liked,
        "total_likes": post.likes.count()
    })
@require_POST
@login_required
def add_comment(request):
    post_id = request.POST.get("post_id")
    text = request.POST.get("text")

    post = get_object_or_404(Post, id=post_id)
    comment = Comment.objects.create(post=post, user=request.user, text=text)

    return JsonResponse({
        "username": request.user.username,
        "text": comment.text,
        "created_at": comment.created_at.strftime("%d %B %Y, %H:%M")
    })
def get_field_advice(field):
    last_history = DiseaseHistory.objects.filter(field=field).order_by('-created_at').first()
    if not last_history:
        return None

    disease = last_history.disease_name

    advice_data = {
        "Blight": {
            "title": "Blight (Yaprak Yanıklığı)",
            "advice": "Mancozeb veya Copper Oxychloride (haftada 1 kez püskürtme yapılmalı).",
            "note": "Erken sabah veya akşam serinliğinde ilaçlama yap."
        },
        "Common_Rust": {
            "title": "Common Rust (Pas Hastalığı)",
            "advice": "Azoxystrobin + Propiconazole karışımı etkili olur.",
            "note": "Nem oranı yüksek olduğunda daha iyi sonuç verir."
        },
        "Gray_Leaf_Spot": {
            "title": "Gray Leaf Spot (Yaprak Leke Hastalığı)",
            "advice": "Pyraclostrobin veya Trifloxystrobin kullan.",
            "note": "Yapraktan püskürtme yapılması önerilir."
        },
        "Red_spider": {
            "title": "Red Spider (Kırmızı Örümcek)",
            "advice": "Abamectin veya Fenpyroximate tercih edilmelidir.",
            "note": "Güneşli saatlerde uygulama yapılmamalıdır."
        },
        "Mold": {
            "title": "Mold (Küf)",
            "advice": "Thiophanate-methyl veya Carbendazim uygundur.",
            "note": "Fazla sulamadan kaçınılmalıdır."
        },
        "sticky_insect": {
            "title": "Sticky Insect (Yapışkan Böcek Zararlısı)",
            "advice": "Neem yağı veya Pyrethrin bazlı organik insektisit kullan.",
            "note": "Biyolojik mücadele yöntemi önerilir; yaprak altlarını kontrol et."
        },
        "Potassium_Deficiency": {
            "title": "Potasyum Eksikliği",
            "advice": "Potasyum nitrat (%13 K) veya Potasyum sülfat (%50 K₂O) kullan.",
            "note": "Sulama öncesi toprak analizi yapılması önerilir."
        },
        "Phosphorus_Deficiency": {
            "title": "Fosfor Eksikliği",
            "advice": "Triple Süper Fosfat (%46 P₂O₅) uygulayın.",
            "note": "Bitkinin erken büyüme döneminde uygulanmalıdır."
        },
    }

    return advice_data.get(disease, {
        "title": disease,
        "advice": "Genel fungusit veya insektisit uygulanabilir.",
        "note": "Hastalığın şiddetine göre ilaç seçimi yapılmalıdır."
    })

@login_required
@require_POST
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id, owner=request.user)
    post.delete()
    messages.success(request, "Gönderi silindi.")
    return redirect('feed')

@login_required
def my_posts(request):
    my_posts = Post.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'my_posts.html', {'my_posts': my_posts})

