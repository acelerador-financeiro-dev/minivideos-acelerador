# Máscara da pessoa (u2net_human_seg) a cada 2 quadros no trecho do modo planilha. Uso: masks.py S n0 n1 out.npy
import sys, subprocess, numpy as np
S = sys.argv[1]; n0, n1 = int(sys.argv[2]), int(sys.argv[3]); out = sys.argv[4]
sys.path.insert(0, S + "/cv4")
import cv2, onnxruntime as ort
so = ort.SessionOptions(); so.intra_op_num_threads = 1
sess = ort.InferenceSession(f"{S}/u2net_human_seg.onnx", so, providers=["CPUExecutionProvider"]); inp = sess.get_inputs()[0].name
cnt = (n1 - n0 + 1) // 2 + 1
cmd = ["ffmpeg", "-v", "error", "-ss", f"{n0/30:.4f}", "-i", f"{S}/raw/base_hdr.mp4", "-frames:v", str(cnt * 2),
       "-vf", "select='not(mod(n\\,2))',scale=320:320:flags=area,format=rgb24", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
res = []; mean = np.array([0.485, 0.456, 0.406]); std = np.array([0.229, 0.224, 0.225]); k5 = np.ones((5, 5), np.uint8)
while len(res) < cnt:
    b = p.stdout.read(320 * 320 * 3)
    if len(b) < 320 * 320 * 3: break
    x = np.frombuffer(b, np.uint8).reshape(320, 320, 3).astype(np.float32) / 255
    x = ((x - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
    o = sess.run(None, {inp: x})[0][0, 0]; o = (o - o.min()) / (o.max() - o.min() + 1e-8)
    m8 = (o * 255).astype(np.uint8)
    # fecha buracos pequenos (mão, microfone) e mantém só as regiões grandes
    hard = (m8 > 128).astype(np.uint8); hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, k5, iterations=2)
    nl, lab, st, _ = cv2.connectedComponentsWithStats(hard)
    keep = np.zeros_like(hard)
    for i in range(1, nl):
        if st[i, cv2.CC_STAT_AREA] > 600: keep[lab == i] = 1
    m8 = np.maximum(m8, (cv2.erode(keep, k5) * 255).astype(np.uint8)) * (cv2.dilate(keep, k5, iterations=2) > 0)
    res.append(m8.astype(np.uint8))
    if len(res) % 100 == 0: print(out, len(res), flush=True)
np.save(out, np.stack(res)); print("OK", out, len(res), flush=True)
