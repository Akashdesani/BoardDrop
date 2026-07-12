import qrcode
import os

def generate_qr(data):

    os.makedirs("qr", exist_ok=True)

    img = qrcode.make(data)

    img.save("qr/qr.png")