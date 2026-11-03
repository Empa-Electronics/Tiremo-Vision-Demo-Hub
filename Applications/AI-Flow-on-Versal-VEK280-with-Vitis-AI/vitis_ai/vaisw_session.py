"""Runs an ONNX model with VAISW: calibration images first, then evaluation images (simulated NPU)."""
import glob
import sys

import numpy as np
import onnxruntime as ort

from yolo_io import to_input

onnx_file, calib_dir, eval_dir, out_file = sys.argv[1:5]
images = lambda d: sorted(glob.glob(f"{d}/*"))

sess = ort.InferenceSession(onnx_file, providers=["CPUExecutionProvider"])
for path in images(calib_dir):                   # calibration: VAISW collects these images
    sess.run(None, {"images": to_input(path)})

results = {}                                     # from here on: the NPU (simulated)
for path in images(eval_dir) if eval_dir != "-" else []:
    name = path.split("/")[-1].rsplit(".", 1)[0]
    results[name] = sess.run(None, {"images": to_input(path)})[0].copy()   # copy: VAISW reuses its output buffers
if out_file != "-":
    np.savez_compressed(out_file, **results)
    print(f"NPU results of {len(results)} images -> {out_file}")
