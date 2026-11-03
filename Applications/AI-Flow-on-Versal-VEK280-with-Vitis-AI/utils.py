"""Helpers for quantize_compile_yolov8s.ipynb: data, drawing, mAP, the NPU tail and the VAISW runs."""
import collections
import copy
import json
import os
import shutil
import subprocess
import sys
import types
import warnings
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import torch
import yaml
from matplotlib import pyplot as plt
from PIL import Image
from torch import nn
from ultralytics.utils.metrics import ap_per_class, box_iou
from ultralytics.utils.tal import make_anchors

ROOT = Path(__file__).parent
COLORS = [(163, 230, 53), (250, 204, 21), (251, 146, 60), (56, 189, 248),
          (244, 114, 182), (167, 139, 250), (45, 212, 191), (248, 113, 113)]
DARK = (30, 34, 40)
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "vitis_ai"))
from yolo_io import IMG_H, IMG_W, letterbox, to_input, to_rgb  # noqa: E402


def evenly_spaced(paths, n):
    """n paths evenly across a sorted list."""
    return [paths[(2 * i + 1) * len(paths) // (2 * n)] for i in range(n)]


class Dataset:
    """The calibration and evaluation images of COCO val2017, their labels and a sample to show. No image is in both."""

    def __init__(self, yaml_path, calib_size, eval_size):
        cfg = yaml.safe_load(open(yaml_path))
        self.names = cfg["names"]
        root = Path(cfg["path"])
        images = sorted((root / cfg["val"]).iterdir())
        self.calib = evenly_spaced(images, calib_size)
        self.val = evenly_spaced(sorted(set(images) - set(self.calib)), eval_size)
        self.labels = {p.stem: self.load_labels(p) for p in self.val}

    def load_labels(self, image):
        """Label file of an image -> classes and x1 y1 x2 y2 boxes in input pixels."""
        label_file = Path(str(image.with_suffix(".txt")).replace("/images/", "/labels/"))
        rows = [l.split() for l in open(label_file) if l.strip()] if label_file.exists() else []   # some have no objects
        a = np.array(rows, np.float32).reshape(-1, 5)
        width, height = Image.open(image).size
        scale, _, _, dx, dy = letterbox(width, height)
        cx, cy = a[:, 1] * width * scale + dx, a[:, 2] * height * scale + dy
        w, h = a[:, 3] * width * scale, a[:, 4] * height * scale
        return a[:, 0], np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 1)

    def sample(self, classes, sizes=(60, 300), max_labels=15):
        """A readable evaluation image: a clearly visible object of these classes, few labels, the most classes."""
        ids = {k for k, v in self.names.items() if v in classes}

        def score(image):
            cls, boxes = self.labels[image.stem]
            sides = np.maximum(boxes[:, 2] - boxes[:, 0], boxes[:, 3] - boxes[:, 1])
            seen = any(int(c) in ids and sizes[0] <= d <= sizes[1] for c, d in zip(cls, sides))
            return seen and len(cls) <= max_labels, len(set(cls.tolist()))

        return max(self.val, key=score)


def rounded(img, x1, y1, x2, y2, radius, color):
    """A filled rectangle with round corners."""
    cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, -1)
    cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, -1)
    for x, y in ((x1 + radius, y1 + radius), (x2 - radius, y1 + radius), (x1 + radius, y2 - radius), (x2 - radius, y2 - radius)):
        cv2.circle(img, (x, y), radius, color, -1, cv2.LINE_AA)


def box(img, x1, y1, x2, y2, color):
    """A thin, slightly faint rectangle with short, stronger corners."""
    x1, y1, x2, y2 = max(int(x1), 0), max(int(y1), 0), min(int(x2), img.shape[1] - 1), min(int(y2), img.shape[0] - 1)
    weight = max(2, round(max(img.shape[:2]) / 650))
    arm = min(max(2 * weight, min(x2 - x1, y2 - y1) // 7), 10 * weight)
    area = img[y1:y2 + 1, x1:x2 + 1]
    panel = area.copy()
    edge = weight - 1                                  # thinner than the corners
    cv2.rectangle(panel, (edge // 2, edge // 2), (x2 - x1 - edge // 2, y2 - y1 - edge // 2), color, edge)
    area[:] = cv2.addWeighted(panel, 0.8, area, 0.2, 0)
    for x, y, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        cv2.line(img, (x, y), (x + dx * arm, y), color, weight)
        cv2.line(img, (x, y), (x, y + dy * arm), color, weight)


def label(img, x, y, text, color):
    """A dark rounded label with a coloured dot, above the point x, y and inside the image."""
    height = max(18, round(max(img.shape[:2]) * 0.02))
    size, thickness = height / 34, max(1, round(height / 24))
    (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, size, thickness)
    width = height + text_w + height // 2
    x1, y2 = min(max(x, 0), img.shape[1] - width), max(y, height)
    y1, x2 = y2 - height, x1 + width
    area = img[y1:y2, x1:x2]
    panel = area.copy()
    rounded(panel, 0, 0, width - 1, height - 1, height // 3, DARK)
    area[:] = cv2.addWeighted(panel, 0.85, area, 0.15, 0)
    cv2.circle(img, (x1 + height // 2, y1 + height // 2), height // 6, color, -1, cv2.LINE_AA)
    cv2.putText(img, text, (x1 + height * 7 // 8, y1 + (height + text_h) // 2), cv2.FONT_HERSHEY_SIMPLEX, size, (255, 255, 255),
                thickness, cv2.LINE_AA)


def draw(rgb, boxes, classes, names, scores=None, color=None):
    """The boxes in the class colours, or in one colour, then the labels on top."""
    img = rgb.copy()
    colors = [color or COLORS[int(c) % len(COLORS)] for c in classes]
    for b, c in zip(boxes, colors):
        box(img, *b[:4], c)
    for i, (b, c) in enumerate(zip(boxes, colors)):
        text = names[int(classes[i])] + (f" {scores[i]:.2f}" if scores is not None else "")
        label(img, int(b[0]), int(b[1]) - 4, text, c)
    return img


def show_predictions(dataset, image, predictions):
    """The labels, if the image has them, then one panel per {title: [N, 6] detections}."""
    rgb = cv2.resize(to_rgb(image), None, fx=2, fy=2)     # twice the size: readable labels
    panels = {}
    if image.stem in dataset.labels:
        cls, gt = dataset.labels[image.stem]
        panels[f"labels ({len(gt)})"] = draw(rgb, gt * 2, cls, dataset.names, color=(255, 255, 255))
    for title, d in predictions.items():
        panels[f"{title} ({len(d)})"] = draw(rgb, d[:, :4] * 2, d[:, 5], dataset.names, d[:, 4])
    fig, axes = plt.subplots(1, len(panels), figsize=(7 * len(panels), 5.5))
    for ax, (title, img) in zip(np.atleast_1d(axes), panels.items()):
        ax.imshow(img)
        ax.set_title(title)
        ax.axis("off")
    plt.tight_layout()
    plt.show()


def show_images(images, most=8):
    images = evenly_spaced(images, min(most, len(images)))
    fig, axes = plt.subplots(1, len(images), figsize=(3.5 * len(images), 2.8))
    for ax, p in zip(np.atleast_1d(axes), images):
        ax.imshow(to_rgb(p))
        ax.axis("off")
    plt.show()


def nms(output, conf=0.25, iou=0.7, max_det=300):
    """Model output [1, 4 + classes, N] (cx cy w h in input pixels, class scores) -> [n, 6] x1 y1 x2 y2 score class."""
    p = output[0].T
    xyxy = np.concatenate([p[:, :2] - p[:, 2:4] / 2, p[:, :2] + p[:, 2:4] / 2], 1)
    cls = p[:, 4:].argmax(1)
    score = p[np.arange(len(p)), 4 + cls]
    keep = score > conf
    xyxy, score, cls = xyxy[keep], score[keep], cls[keep]
    if not len(xyxy):
        return np.zeros((0, 6))
    xywh = np.c_[xyxy[:, :2], xyxy[:, 2:] - xyxy[:, :2]]
    kept = cv2.dnn.NMSBoxesBatched(xywh.tolist(), score.tolist(), cls.tolist(), conf, iou)
    return np.concatenate([xyxy, score[:, None], cls[:, None]], 1)[np.array(kept, int).reshape(-1)[:max_det]]


def session(onnx_file):
    return ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])


def predict(sess, image, conf=0.25):
    return nms(sess.run(None, {"images": to_input(image)})[0], conf)


def mean_ap(dets, labels):
    """mAP like Ultralytics' val. dets / labels: {image: [N, 6]} / {image: (classes, xyxy)}."""
    iouv = torch.linspace(0.5, 0.95, 10)
    tp, conf, pcls, tcls = [], [], [], []
    for k, d in dets.items():
        gc, gb = labels[k]
        correct = np.zeros((len(d), 10), bool)
        if len(d) and len(gc):
            iou = box_iou(torch.tensor(gb), torch.tensor(d[:, :4], dtype=torch.float32))
            iou = (iou * (torch.tensor(gc)[:, None] == torch.tensor(d[:, 5])[None])).numpy()
            for j, t in enumerate(iouv.tolist()):
                m = np.array(np.nonzero(iou >= t)).T
                if len(m):
                    m = m[iou[m[:, 0], m[:, 1]].argsort()[::-1]]
                    m = m[np.unique(m[:, 1], return_index=True)[1]]
                    m = m[np.unique(m[:, 0], return_index=True)[1]]
                    correct[m[:, 1].astype(int), j] = True
        tp.append(correct); conf.append(d[:, 4]); pcls.append(d[:, 5]); tcls.append(gc)
    r = ap_per_class(np.concatenate(tp), np.concatenate(conf), np.concatenate(pcls), np.concatenate(tcls))
    classes = r[6].tolist() if hasattr(r[6], "tolist") else list(r[6])
    return r[2].mean(), r[3].mean(), r[5][:, 0].mean(), r[5].mean(), dict(zip(classes, r[5][:, 0].tolist()))


class Scoreboard:
    """mAP of each step, side by side, with two common classes."""

    def __init__(self, dataset, classes=("person", "car")):
        self.dataset, self.rows = dataset, {}
        self.classes = {k: v for k, v in dataset.names.items() if v in classes}

    def add(self, name, dets):
        self.rows[name] = mean_ap(dets, self.dataset.labels)
        heads = "  ".join(f"{v:>6s}" for v in self.classes.values())
        print(f"{'':30s}     P      R  mAP50  mAP50-95  {heads}")
        for k, v in self.rows.items():
            aps = "  ".join(f"{v[4].get(c, float('nan')):6.3f}" for c in self.classes)
            print(f"{k:30s} {'  '.join(f'{x:.3f}' for x in v[:4])}     {aps}")

    def add_session(self, name, sess):
        self.add(name, {p.stem: predict(sess, p, conf=0.001) for p in self.dataset.val})

    def add_results(self, name, npz_file):
        npz = np.load(npz_file)
        self.add(name, {p.stem: nms(npz[p.stem], conf=0.001) for p in self.dataset.val})


def export_default(yolo, onnx_file):
    """The model as Ultralytics exports it, with its decoding, at the model input size."""
    out = yolo.export(format="onnx", imgsz=(IMG_H, IMG_W), opset=17, simplify=True, batch=1, device="cpu")
    return Path(shutil.move(out, onnx_file))


def npu_tail_forward(self, x):
    """Detect head with the decoding per scale, in NPU operations: no Transpose, and one Reshape per scale at the end."""
    maps = []
    for i in range(self.nl):
        box, cls = self.cv2[i](x[i]), self.cv3[i](x[i])
        sides = [self.dfl.conv(box[:, 16 * s : 16 * (s + 1)].softmax(1)) for s in range(4)]
        xywh = self.ltrb_to_xywh[i](torch.cat(sides, 1)) + getattr(self, f"anchor_map{i}")
        h, w = xywh.shape[2:]
        maps.append(torch.cat((xywh, cls.sigmoid()), 1).reshape(1, 4 + self.nc, int(h) * int(w)))
    return torch.cat(maps, 2)


def export_npu_tail(yolo, onnx_file):
    """The same model with `npu_tail_forward`; the weights do not change."""
    model = copy.deepcopy(yolo.model).float().eval().cpu()
    detect = model.model[-1]
    feats = [torch.zeros(1, 1, IMG_H // int(s), IMG_W // int(s)) for s in detect.stride]
    anchors = make_anchors(feats, detect.stride, 0.5)[0]             # [N, 2], in the order of the original tail
    detect.ltrb_to_xywh = nn.ModuleList()
    start = 0
    # cx = ax + (r - l) / 2, cy = ay + (b - t) / 2, w = l + r, h = t + b, all times the stride
    matrix = torch.tensor([[-.5, 0, .5, 0], [0, -.5, 0, .5], [1, 0, 1, 0], [0, 1, 0, 1]])[..., None, None]
    for i, stride in enumerate(detect.stride.tolist()):
        h, w = feats[i].shape[2:]
        conv = nn.Conv2d(4, 4, 1, bias=False)
        conv.weight.data = stride * matrix
        detect.ltrb_to_xywh.append(conv)
        a = anchors[start : start + h * w] * stride
        start += h * w
        detect.register_buffer(f"anchor_map{i}", torch.cat((a.T.reshape(1, 2, h, w), torch.zeros(1, 2, h, w)), 1))
    detect.forward = types.MethodType(npu_tail_forward, detect)
    with torch.no_grad(), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        torch.onnx.export(model, torch.zeros(1, 3, IMG_H, IMG_W), str(onnx_file), input_names=["images"],
                          output_names=["output0"], opset_version=17, do_constant_folding=True, dynamo=False)
    return Path(onnx_file)


def compare_outputs(sess_a, sess_b, images):
    """Largest difference of two models with the same output, boxes and scores apart."""
    box, score = 0, 0
    for p in images:
        x = {"images": to_input(p)}
        a, b = sess_a.run(None, x)[0], sess_b.run(None, x)[0]
        box, score = max(box, np.abs(a[:, :4] - b[:, :4]).max()), max(score, np.abs(a[:, 4:] - b[:, 4:]).max())
    print(f"{len(images)} images, largest difference: boxes {box:.4f} px, scores {score:.7f}")


def link_images(images, folder):
    """A folder of links to the images, which stay in the dataset: no second copy on the disk."""
    folder = Path(folder)
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for p in images:
        (folder / p.name).symlink_to(p.resolve())
    return folder


class Vaisw:
    """Runs Python with VAISW in the Vitis AI 6.1 container, for one NPU IP."""

    def __init__(self, workspace, container, npu_ip):
        self.vitis_ai, self.container, self.npu_ip = f"{workspace}/src/Vitis-AI-6.1", container, npu_ip
        state = ["docker", "inspect", "-f", "{{.State.Running}}", container]
        if subprocess.run(state, capture_output=True, text=True).stdout.strip() != "true":
            subprocess.run(["docker", "rm", container], capture_output=True)
            subprocess.run(["docker", "run", "-d", "--name", container, "--shm-size=8g", "-v", f"{workspace}:{workspace}",
                            "vai-npu-sw:6.1", "sleep", "infinity"], check=True)

    def run(self, workdir, onnx_file, calib_dir, eval_dir, out_file, env):
        """vaisw_session.py in the container, in workdir. Saves the log to workdir/vaisw.log and returns its lines."""
        os.makedirs(workdir, exist_ok=True)
        shutil.rmtree(env.get("VAISW_SNAPSHOT_DIRECTORY", ""), ignore_errors=True)
        args = f"{ROOT}/vitis_ai/vaisw_session.py {onnx_file} {calib_dir} {eval_dir} {out_file}"
        cmd = (f"source {self.vitis_ai}/npu_ip/settings.sh {self.npu_ip} > /dev/null && "
               f"PYTHONPATH={ROOT}/vitis_ai:$PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python3 {args}; rc=$?; "   # keep VAISW's PYTHONPATH
               f"rm -rf {workdir}/home {workdir}/calib_cfg_frontend.toml {workdir}/vaisw_*.log {workdir}/reporting.json; "     # VAISW's working files
               f"find {workdir} -depth -type d -empty -delete; "                 # and empty copies of its output paths
               f"chown -R {os.getuid()}:{os.getgid()} {ROOT}/result_*; exit $rc")         # the container runs as root
        flags = [f"-e{k}={v}" for k, v in env.items()]
        p = subprocess.run(["docker", "exec", "-w", str(workdir), *flags, self.container, "bash", "-c", cmd],
                           capture_output=True, text=True)
        log = (p.stdout + p.stderr).replace("\x1b", "")
        (Path(workdir) / "vaisw.log").write_text(log)
        assert p.returncode == 0 and "[VAISW]" in log, "\n".join(log.splitlines()[-30:])
        return log.splitlines()

    def inspect(self, onnx_file, image, out_dir, env):
        """Partition the model (no calibration) and print where each part runs."""
        out_dir = Path(out_dir)
        shutil.rmtree(out_dir, ignore_errors=True)
        image_dir = link_images([image], out_dir / "image")
        print_summary(self.run(out_dir, onnx_file, image_dir, "-", "-", env))
        for g in json.load(open(env["VAISW_DEBUG_GRAPHEXECUTIONREPORTPATH"])):
            ops = collections.Counter(l["type"].replace("VAISW_", "") for l in g["layers"])
            print(f"\n{g['name']}: {'NPU' if g['execution'] == 'VAISW' else 'CPU'}, {len(g['layers'])} layers\n   {dict(ops)}")


def print_summary(log):
    """What VAISW says about the partition and the precision."""
    keys = ("MACs", "FPGA", "CPU  ", "subgraph", "precision:", "NPU results")
    skip = ("Execution will", "snapshot", "Total")
    clean = lambda line: line.replace("[0;32m", "").replace("[0m", "").replace("[VAISW]", "").strip()
    print("\n".join(clean(l) for l in log if any(k in l for k in keys) and not any(k in l for k in skip)))


def saved_detections(npz_file, image):
    """Detections of one image from the saved NPU results."""
    return nms(np.load(npz_file)[image.stem])


def print_snapshot(snapshot):
    """The target of a snapshot, its size, and the steps of main.json around the NPU call."""
    export = Path(snapshot) / "embedded_export"
    infos = json.load(open(next(export.glob("*/snapshot.dump.infos"))))
    size = sum(f.stat().st_size for f in Path(snapshot).rglob("*") if f.is_file()) / 1e6
    print(f"target: NPU IP {infos['boardname']}, bitstream timestamp {infos['timestamp']}; {size:.0f} MB")
    layers = [v["layer"]["params"]["type"] for v in json.load(open(export / "main.json")).values() if "layer" in v]
    print("main.json:", " -> ".join(layers))
