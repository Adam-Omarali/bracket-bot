from ultralytics import YOLO

model = YOLO("commands/best_bottle.pt")

model.export(format="ncnn")