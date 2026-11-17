<p align="center">
  <img src="assets/logo-empa.svg" alt="Empa" width="220">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-tiremo-vision-dark.svg">
    <img src="assets/logo-tiremo-vision-light.svg" alt="Tiremo Vision" width="90">
  </picture>
</p>

<h1 align="center">Lidar Person Detection</h1>

<p align="center">
  <b>Kria KR260</b><br>
  A low-cost 2-D lidar on a servo becomes a 3-D sensor that tells people from objects
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Kria%20KR260-65b32e?style=flat-square">
  <img alt="Compute" src="https://img.shields.io/badge/compute-DPU%20%2B%20PL%20filter%20%2B%20Arm-65b32e?style=flat-square">
  <img alt="Workload" src="https://img.shields.io/badge/workload-3--D%20person%20detection-65b32e?style=flat-square">
  <img alt="Model" src="https://img.shields.io/badge/model-PersonNet-65b32e?style=flat-square">
</p>

<!-- TODO hero photo: the KR260 with the lidar on its servo and the person map on the display. Save as assets/hero.jpg, then un-comment.
<p align="center">
  <img src="assets/hero.jpg" alt="" width="100%">
  <br>
  <sub></sub>
</p>
-->

## Summary

A YDLIDAR X2, a low-cost 2-D laser scanner, is tilted up and down by a servo so that it sweeps the room in 3-D. On a Kria KR260, our own lidar_filter block in the programmable logic cleans each turn of points and turns it into x, y and z. The Arm cores build a map of the ground and the objects on it, and a small network on the DPU (deep-learning processing unit) decides for each object whether it is a person. On the display, every person in the map gets a number, and a HUMAN DETECTED banner appears when someone is in view. The sensor uses a laser, so it works in the dark and keeps no camera images.

## Highlights

- Our own HLS accelerator and the AMD DPU share one bitstream and one DDR, with no lidar data passing through the CPU caches.
- Point filtering takes 0.51 ms per turn in the programmable logic, and classification 0.174 ms per object on the DPU.
- A 2-D scanner and a servo give a 3-D view at a fraction of the cost of a 3-D lidar.
- No camera images are taken, which suits privacy-sensitive sites and dark areas.

## Specifications

| Category | Details |
|:--|:--|
| Use cases | person detection around machines, safety zones, entrance monitoring |
| Target markets | robotics, machine and warehouse safety, smart buildings |
| Platform | Kria KR260 Robotics Starter Kit, Zynq UltraScale+ K26 SOM |
| Compute | DPU B1024 (INT8) and the lidar_filter HLS block in the programmable logic, Arm Cortex-A53 for mapping |
| Models and algorithms | lidar_filter with edge filter, thin rule, line median, window, time and cross grid and x y z conversion. PersonNet on a 2×48×32 front view per object |
| Inputs | YDLIDAR X2 over USB, servo angle through a U2D2 adapter |
| Outputs | display panel over DisplayPort with numbered people and status rows |
| Software and tools | Vivado and Vitis HLS, Vitis AI DPU flow, Linux on the KR260 |
| Data | front views of objects taken from the lidar map |

## System

![System diagram: the YDLIDAR X2 and the servo connect to the Arm cores of the KR260. The lidar_filter block in the PL cleans the points, the Arm cores build the map, the DPU runs PersonNet on each object, and the display panel shows the people found. All blocks share DDR, and the PL signals completion through an interrupt controller.](assets/system-diagram.svg)

1. The lidar sends one turn of about 250 samples every 95 ms over USB.
2. The main thread sorts the turn by angle and adds the servo angle, read once per turn.
3. The turn and 64 settings go to DDR, and lidar_filter in the programmable logic writes the cleaned x, y and z points back in 0.51 ms.
4. A worker thread adds the points to the map as one slice and finds the ground, the objects and the mesh.
5. Once per sweep, each object becomes a 2×48×32 front view, and PersonNet on the DPU gives the chance that it is a person.
6. The display shows the numbered people, the HUMAN DETECTED banner and the status rows.

## Performance

| Metric | Value | Conditions |
|:--|:--|:--|
| Point filtering | 0.51 ms per turn | lidar_filter in the programmable logic |
| Person classification | 0.174 ms per object | PersonNet on the DPU B1024 |
| Lidar input | about 250 samples every 95 ms | YDLIDAR X2 |
| Map update | 80 to 200 ms | Arm worker thread |
| Programmable logic | 47 % LUT, 75 % BRAM, 22 % DSP | after routing, timing met at +0.003 ns |

## Development

The hardware is one programmable logic design, lidar-b1024, that puts the AMD DPU and our lidar_filter HLS block side by side. Both run at 300 MHz, with the DPU's DSP blocks at 600 MHz. The Arm cores reach their registers through the HPM0 ports and hear back through an interrupt controller, while the data moves through five 128-bit ports straight to DDR. The software on the Arm cores assembles each turn, builds the map and runs a person server that sends each object's front view to the DPU.

A few points shaped the design:

- The filtering chain runs in the programmable logic in 0.51 ms per turn, which leaves the Arm cores free for mapping.
- Lidar turns, settings, weights and results travel through shared DDR, never through the CPU caches.
- Control and data never share a path: registers go through HPM0, completion comes back as an interrupt, data uses the HP ports.

Next, the map building, now the slowest step, will be made faster.

## Setup

- Kria KR260, which runs the full pipeline
- YDLIDAR X2 on a servo with a U2D2 adapter, for the 3-D sweep
- Display panel on DisplayPort, for the person map

## Resources

- [Kria KR260 Robotics Starter Kit](https://www.amd.com/en/products/system-on-modules/kria/k26/kr260-robotics-starter-kit.html): board overview and documentation
- [Vitis HLS user guide (UG1399)](https://docs.amd.com/r/en-US/ug1399-vitis-hls): the tool used for lidar_filter
- [Vitis AI documentation](https://vitisai.docs.amd.com/): from a trained model to the DPU
- [YDLIDAR](https://www.ydlidar.com/): maker of the X2 2-D lidar

## Related demos

- [Smart Camera Person Tracker](../kv260-smart-camera-person-tracker/): people tracked with stable IDs on a Kria KV260
- [One PCIe Card, Many Accelerators](../deico-z7015-pcie-accelerator-switching/): FPGA accelerators swapped over PCIe in about 3 s
- [Air-to-Ground Surveillance](../alinx-z7a-air-to-ground-surveillance/): four drone cameras and one person detector on the NPU

## Contact

Questions about this demo: [ai@empa.com](mailto:ai@empa.com)

<sub>Product names are trademarks of their respective owners. Last updated 2026-11.</sub>
