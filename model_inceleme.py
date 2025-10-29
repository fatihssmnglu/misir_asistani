import torch

# Model dosyasını yükle
state_dict = torch.load("hastalik/corn_disease_model.pth", map_location="cpu")

# Anahtar (katman isimleri) listesini göster
print("\n🔹 Modeldeki Katmanlar:")
for i, key in enumerate(state_dict.keys()):
    print(i, key)
    if i > 50:  # ilk 50 tanesini göster, fazla olmasın
        break

# Çıkış katmanının boyutunu göster (örneğin 4, 5, 12 gibi)
if "fc.weight" in state_dict:
    print("\n⚙️ Çıkış Katmanı Boyutu:", state_dict["fc.weight"].shape)
