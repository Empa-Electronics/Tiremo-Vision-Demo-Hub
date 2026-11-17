<p align="center">
  <img src="assets/logo-empa.svg" alt="Empa" width="220">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-tiremo-vision-dark.svg">
    <img src="assets/logo-tiremo-vision-light.svg" alt="Tiremo Vision" width="90">
  </picture>
</p>

<h1 align="center">Smart Camera Person Tracker</h1>

<p align="center">
  <b>Kria KV260</b><br>
  Every person keeps a stable ID through crossings, occlusion and leaving the view
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Kria%20KV260-65b32e?style=flat-square">
  <img alt="Compute" src="https://img.shields.io/badge/compute-DPU%20%2B%20Arm%20%2B%20GPU%20%2B%20VCU-65b32e?style=flat-square">
  <img alt="Workload" src="https://img.shields.io/badge/workload-multi--person%20tracking-65b32e?style=flat-square">
  <img alt="Model" src="https://img.shields.io/badge/model-RefineDet%20%2B%20ReID-65b32e?style=flat-square">
</p>

<!-- TODO hero photo: the KV260 with the camera module and the tactical HUD on the monitor. Save as assets/hero.jpg, then un-comment.
<p align="center">
  <img src="assets/hero.jpg" alt="" width="100%">
  <br>
  <sub></sub>
</p>
-->

## Summary

A Kria KV260 with a MIPI camera finds people, gives each one a number and keeps that number as they move, cross paths, or leave the view and come back. RefineDet detects people on the DPU (deep-learning processing unit), and a ReID (re-identification) network describes how each person looks, so the tracker can tell people apart. A tactical HUD is drawn straight into the live video on DisplayPort, and the same video can go out as an H.264 RTSP stream from the hard video encoder. The programmable logic is AMD's Smart Camera design, used unchanged, so all of the work is in the application. On the screen, every person carries a target number and a score, and an operator can pick one person to follow.

## Highlights

- IDs hold when people cross or are briefly hidden, and a person who returns within 120 s gets the old ID back.
- The video stays at camera rate whatever the detection rate, because the camera buffer goes to the display with no copy.
- ReID runs only where it changes a decision, so the DPU time stays close to the detector's alone.
- No hardware build is needed. The application runs on the stock Smart Camera platform under Ubuntu.

## Specifications

| Category | Details |
|:--|:--|
| Use cases | multi-person tracking, people counting, following an operator-selected person, live video monitoring |
| Target markets | security, retail analytics, building and site monitoring |
| Platform | Kria KV260 Vision AI Starter Kit, Zynq UltraScale+ K26 SOM |
| Compute | DPU B3136 (INT8) in the programmable logic, 4× Arm Cortex-A53, Mali-400 GPU, VCU video encoder |
| Models and algorithms | RefineDet (pruned, 480×360) for person detection, ResNet-18 ReID for appearance, Kalman filter, Hungarian matching, ByteTrack and a ReID gallery |
| Inputs | AR1335 sensor with AP1302 ISP, MIPI CSI-2 with 4 lanes, NV12 |
| Outputs | DisplayPort at the monitor's native mode with the HUD, H.264 RTSP stream (MJPEG at 720p as a fallback) |
| Software and tools | Ubuntu 22.04 for Kria, Vitis AI Library, GStreamer 1.18 with gst-rtsp-server, OpenCV 4.5, C++17 and CMake |
| Data | pre-trained models from the Kria AI-box distribution, MOT16 sequences for offline tracker evaluation |

## System

![System diagram: the AR1335 camera module feeds the MIPI CSI-2 receiver in the PL of the KV260. The DPU runs RefineDet and ReID, the Arm cores and Mali-400 GPU pre-process, track and draw the HUD, and the result goes to a DisplayPort monitor and, through the VCU, to an RTSP client.](assets/system-diagram.svg)

1. The AP1302 ISP on the camera module sends NV12 frames over MIPI CSI-2, and the Smart Camera design in the programmable logic writes them to DDR.
2. The Mali-400 GPU reads the frame in place and renders a 480×360 network input, which keeps the copy and colour conversion off the Arm cores.
3. The DPU runs RefineDet on the frame, and ReID only on the people where the tracker needs it: new people, overlaps and a periodic refresh.
4. The tracker on the Arm cores matches people across frames with a Kalman filter, Hungarian matching and the ReID gallery.
5. The HUD is drawn into the same camera buffer that DisplayPort shows, and the VCU encodes it to H.264 for the RTSP stream.

## Performance

| Metric | Value | Conditions |
|:--|:--|:--|
| Video rate | 30 FPS | monitor's native mode, no frame copy |
| GPU pre-processing | saves about 20 ms per frame | against CPU copy, resize and colour conversion at 1440p |
| ReID distance, same person | 0.05 to 0.35 | up to about 0.5 with a large change in pose or light |
| ReID distance, different people | 0.65 to 0.85 | same camera and scene |
| ID memory | 120 s | gallery of lost tracks, 10 appearance features each |

## Development

The application is written in C++17 on top of the stock Smart Camera platform, after a first Python prototype that decoded RefineDet directly on the Vitis AI runtime. GStreamer runs the camera and display path, a worker thread runs detection, ReID and the tracker beside it, and an in-process RTSP server publishes the stream. The same tracking pipeline also runs offline on MOT16 sequences, which made it possible to compare tracker settings with standard metrics.

A few problems were solved along the way:

- Copying frames out of uncached camera memory held the display to about 20 FPS at 1440p. Capturing straight into display buffers removed the copy.
- Pre-processing on the CPU cost about 20 ms per frame. The Mali-400 now does it and renders into a buffer that is read twice as fast as with glReadPixels.
- The Vitis AI Library reads the detection threshold from the model file and has no setter. A copy of the model with a low floor lets the application change the threshold live.
- The video encoder crashed when it was created and destroyed for each RTSP session. It now stays in the main pipeline behind a valve.

Next, the ReID distances will be tuned on more cameras and scenes.

## Setup

- Kria KV260 with the kv260-smartcam platform loaded, which runs the full pipeline
- AR1335 MIPI camera module on the IAS0 connector, for the live input
- DisplayPort monitor, for the HUD
- Laptop on the network with VLC or ffplay, for the RTSP stream

## Resources

- [Kria KV260 Vision AI Starter Kit](https://www.amd.com/en/products/system-on-modules/kria/k26/kv260-vision-starter-kit.html): board overview and documentation
- [Kria Smart Camera application](https://xilinx.github.io/kria-apps-docs/kv260/2022.1/build/html/docs/smartcamera/smartcamera_landing.html): the platform this demo runs on
- [Vitis AI documentation](https://vitisai.docs.amd.com/): from a trained model to the DPU
- [MOT Challenge](https://motchallenge.net/): the benchmark used to evaluate the tracker
- [GStreamer RTSP server](https://gstreamer.freedesktop.org/documentation/gst-rtsp-server/): the streaming library

## Related demos

- [Air-to-Ground Surveillance](../alinx-z7a-air-to-ground-surveillance/): four drone cameras and one person detector on the NPU
- [Lidar Person Detection](../kr260-lidar-person-detection/): people found in a 3-D lidar sweep, in the dark
- [ADAS Multi-Task Perception](../kv260-adas-multitask-perception/): five perception tasks in one network at 30 FPS

## Contact

Questions about this demo: [ai@empa.com](mailto:ai@empa.com)

<sub>Product names are trademarks of their respective owners. Last updated 2026-11.</sub>
