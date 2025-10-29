import torch
import torch.nn as nn
import torchvision.models as models

def create_model(num_classes=12):
    model = models.resnet50(pretrained=False)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model
