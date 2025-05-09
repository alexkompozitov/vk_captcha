import os, io
import numpy as np
import onnxruntime as ort
import requests
from PIL import Image
from flask import Flask, request, jsonify

cfg = {
    'classifier': {'path': "models/type_classifier.onnx", 'shape': (80, 208, 3)},
    'en': {'path': "models/en2.onnx", 'chars': ['z','s','h','q','d','v','2','7','8','x','y','5','e','a','u','4','k','n','m','c','p']},
    'ru': {'path': "models/ru2.onnx", 'chars': ['д','ж','ф','ш','т','у','к','х','а','7','с','5','2','е','р','м']}
}

os.makedirs("captchas", exist_ok=True)

sessions = {}
for k,v in cfg.items():
    s = ort.InferenceSession(v['path'])
    i = s.get_inputs()[0].name
    o = s.get_outputs()[0].name
    sessions[k] = (s, i, o)

maps = {k: {i+1:c for i,c in enumerate(v['chars'])} for k,v in cfg.items() if k!='classifier'}

def preprocess(img, shape, gray=False):
    im = Image.open(io.BytesIO(img)).convert('L' if gray else 'RGB') \
             .resize((shape[1], shape[0]), Image.LANCZOS)
    a = np.array(im, dtype=np.float32) / 255
    if gray:
        a = a.T[:, :, None]
    return a[None, ...]

def decode(preds, m):
    texts, confs = [], []
    for p in preds:
        ids = np.argmax(p, -1)
        ps = np.max(p, -1)
        seq, prev = [], -1
        for idx, prob in zip(ids, ps):
            if idx and idx != prev:
                seq.append((idx, prob))
            prev = idx
        text = ''.join(m.get(i, '') for i,_ in seq)
        texts.append(text)
        confs.append(float(np.mean([pr for _,pr in seq])) if seq else 0.0)
    return texts, confs

app = Flask(__name__)

@app.route('/solve_captcha', methods=['POST'])
def solve():
    sid = request.json.get('sid','')
    if not sid.isdigit(): 
        return jsonify(error="invalid sid"), 400

    url = (f"https://vk.com/captcha.php?sid={sid}"
           "&source=check_user_action_validate%2Bmail_send"
           "&app_id=6121396&device_id=&s=1&resized=1")
    r = requests.get(url)
    if r.status_code != 200: 
        return jsonify(error="download failed"), 500
    img = r.content

    s,i,o = sessions['classifier']
    prob = s.run([o], {i: preprocess(img, cfg['classifier']['shape'])})[0][0][0]
    typ = 'en' if prob >= 0.5 else 'ru'
    s,i,o = sessions[typ]
    texts, confs = decode(
        s.run([o], {i: preprocess(img, (80,208), gray=True)})[0],
        maps[typ]
    )

    ans = texts[0].replace('|unk|','')
    conf = confs[0]
    with open(f"captchas/{ans}-{sid}.jpg",'wb') as f:
        f.write(img)

    return jsonify(
        answer=ans,
        confidence=conf,
        type=typ,
        classifier_confidence=float(prob)
    )

if __name__=='__main__':
    app.run(host='0.0.0.0', port=8888)
