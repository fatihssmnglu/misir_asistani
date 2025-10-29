import random
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

def send_verification_email(profile, force=False):
    now = timezone.now()
    # 30 saniyeden kısa sürede tekrar gönderilmesin
    if profile.last_email_sent_at and (now - profile.last_email_sent_at).total_seconds() < 30 and not force:
        raise ValueError("Çok sık e-posta gönderiliyor. Lütfen bekleyin.")

    code = str(random.randint(100000, 999999))  # 6 haneli kod
    profile.email_verification_code = code
    profile.email_verification_expiry = now + timedelta(minutes=10)
    profile.email_verification_attempts = 0
    profile.last_email_sent_at = now
    profile.save()

    subject = "🌽 Mısır Asistanı - E-posta Doğrulama Kodu"
    message = (
        f"Merhaba {profile.user.username},\n\n"
        f"E-posta doğrulama kodunuz: {code}\n\n"
        f"Bu kod 10 dakika geçerlidir.\n\n"
        f"Eğer bu işlemi siz başlatmadıysanız, bu e-postayı yok sayabilirsiniz."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [profile.user.email],
        fail_silently=False,
    )
