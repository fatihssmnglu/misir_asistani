from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# 🔹 1. Köy (Village)
class Village(models.Model):
    name = models.CharField(max_length=100, unique=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.district or ''})".strip()


# 🔹 2. Kullanıcı Profili
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True, null=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    is_farmer = models.BooleanField(default=True)  # çiftçi mi?
    registered_at = models.DateTimeField(auto_now_add=True)

    # ✅ E-posta doğrulama alanları
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_verification_expiry = models.DateTimeField(null=True, blank=True)
    email_verification_attempts = models.IntegerField(default=0)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username

    def email_code_is_valid(self, code):
        """Girilen e-posta doğrulama kodunun geçerli olup olmadığını kontrol eder."""
        if (
            self.email_verification_code == code
            and self.email_verification_expiry
            and self.email_verification_expiry > timezone.now()
        ):
            return True
        return False

    def mark_email_verified(self):
        """E-posta doğrulaması tamamlandığında çağrılır."""
        self.is_email_verified = True
        self.email_verification_code = None
        self.email_verification_expiry = None
        self.email_verification_attempts = 0
        self.save()

# 🔹 3. Tarla (Field)
class Field(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fields')
    village = models.ForeignKey('Village', on_delete=models.SET_NULL, null=True, blank=True)  # ✅ eklendi
    name = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=50, blank=True)
    area_size = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    soil_type = models.CharField(max_length=50, blank=True)
    irrigation_type = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.owner.username})"



# 🔹 4. Hastalık Raporu (Disease Report)
class Report(models.Model):
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='reports/')
    predicted_label = models.CharField(max_length=100)
    confidence = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.predicted_label} ({self.created_by})"


# 🔹 5. Mesajlaşma Sistemi (Chat)
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender.username} → {self.receiver.username}"
    

class ChatMessage(models.Model):
    village = models.ForeignKey(Village, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)  # 🖼️ resim alanı eklendi
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.text:
            return f"{self.village.name} - {self.sender.username}: {self.text[:30]}"
        return f"{self.village.name} - {self.sender.username}: 🖼️ (Görsel)"


class DiseaseHistory(models.Model):
    field = models.ForeignKey(Field, on_delete=models.CASCADE, related_name='disease_history')
    detected_by = models.ForeignKey(User, on_delete=models.CASCADE)
    disease_name = models.CharField(max_length=100)
    suggestion = models.TextField(blank=True)
    image = models.ImageField(upload_to='disease_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.field.name} - {self.disease_name}"




# 🔹 6. Uyarı Sistemi (Alert)
class Alert(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Bilgi'),
            ('warning', 'Uyarı'),
            ('critical', 'Kritik')
        ],
        default='info'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent = models.BooleanField(default=False)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.severity})"
    
class Post(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="posts/", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_for_sale = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_posts", blank=True)

    # 🌾 yeni eklendi
    CATEGORIES = [
        ('misir', '🌽 Mısır'),
        ('bugday', '🌾 Buğday'),
        ('mercimek', '🌱 Mercimek'),
        ('sebze', '🥕 Sebze'),
        ('hayvancilik', '🐄 Hayvancılık'),
        ('genel', '🗣️ Genel'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORIES, default='genel')

    class Meta:
        ordering = ["-created_at"]

    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

    

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.text[:30]}"


