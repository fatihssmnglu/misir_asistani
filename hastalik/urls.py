from django.urls import path
from . import views


urlpatterns = [
    # 🧠 Hastalık tahmini
    path('upload/', views.upload_and_predict, name='upload_and_predict'),

    # 🏠 Ana sayfa
    path('', views.home, name='home'),
       path('feed/', views.feed, name='feed'),
       path('trade/', views.trade_center, name='trade_center'),


    # 🔐 Kullanıcı işlemleri
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    
    path('logout/', views.logout_user, name='logout'),
     path('verify-email/<int:user_id>/', views.verify_email, name='verify_email'),
    path('verify-email/<int:user_id>/resend/', views.resend_email, name='resend_email'),

    path("feed/new/", views.create_post, name="create_post"),
    path("feed/like/", views.like_post, name="like_post"),


    path('field/<int:field_id>/history/', views.field_history, name='field_history'),
    path("field/delete/<int:field_id>/", views.delete_field, name="delete_field"),




    # 🌾 Tarla işlemleri
    path('add_field/', views.add_field, name='add_field'),
    path('fields/', views.field_list, name='field_list'),
    path('field/<int:field_id>/', views.field_detail, name='field_detail'),

    # 🌾 Köy sohbeti
    path('chat/', views.village_chat, name='village_chat'),
    path('chat/get/<int:village_id>/', views.get_messages, name='get_messages'),
    path('add_village_if_not_exists/', views.add_village_if_not_exists, name='add_village_if_not_exists'),

    # ⚠️ Uyarılar
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/new/', views.create_alert, name='create_alert'),


    path("feed/comment/", views.add_comment, name="add_comment"),
    path('feed/delete/<int:post_id>/', views.delete_post, name='delete_post'),
    
  
   path('feed/my/', views.my_posts, name='my_posts'),

    


]
