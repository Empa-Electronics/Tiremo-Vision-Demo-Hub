<p align="center">
  <img src="Additionals/logo-empa.svg" alt="Empa" width="220">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Additionals/logo-tiremo-vision-dark.svg">
    <img src="Additionals/logo-tiremo-vision-light.svg" alt="Tiremo Vision" width="90">
  </picture>
</p>

<h1 align="center">Uçta Yapay Zeka Demo Merkezi</h1>

<p align="center">
  AMD gömülü platformları üzerinde çalışan yapay zeka uygulamaları, dokümantasyonları ve kaynak kodlarıyla
</p>

<p align="center">
  <a href="README.md">English</a> · Türkçe
</p>

## Hoş geldiniz

Bu repository, Versal ve Zynq UltraScale+ adaptif SoC'ler ile Kria modülleri gibi AMD gömülü platformları üzerindeki uçta yapay zeka çalışmalarımızı bir araya getirir. Aşağıdaki her çalışmanın kendi sayfası vardır. Bu sayfalar uygulamanın ne yaptığını, sistemin nasıl kurulduğunu ve nasıl bir performans gösterdiğini anlatır. Kaynak kodu paylaşılan çalışmalarda kod da aynı klasörde yer alır.

Sayfalar iki tür okuyucu düşünülerek yazılmıştır. Kısa bir fikir edinmek istiyorsanız her sayfanın başındaki özet ve öne çıkanlar yeterlidir. Benzer sistemler geliştiriyorsanız sistem şeması, performans değerleri ve geliştirme notları ayrıntılara iner.

Demo sayfaları İngilizcedir.

## Demolar

| Demo | Platform | Açıklama |
|:--|:--|:--|
| [Air-to-All-Around Vision Tracking](Applications/vek280-drone-vision-tracking/) | Versal AI Edge VEK280 | Yapay zeka kontrollü bir drone yalnızca kamerasıyla uçar, nesne tespiti AI Engine NPU üzerinde çalışır |
| [Air-to-Ground Surveillance](Applications/alinx-z7a-air-to-ground-surveillance/) | Zynq UltraScale+ (ALINX Z7-A) | Drone üzerindeki dört kamera ve tamamı NPU üzerinde çalışan bir kişi tespit modeli |
| [ADAS Multi-Task Perception](Applications/kv260-adas-multitask-perception/) | Kria KV260 | Tek bir ağ ile beş sürüş algılama görevi, 30 FPS hızında |
| [YOLOv8s on the Versal NPU with Vitis AI 6.1](Applications/AI-Flow-on-Versal-VEK280-with-Vitis-AI/) | Versal AI Edge VEK280 | YOLOv8s modelini NPU için adım adım nicemleyen ve derleyen bir notebook, kaynak koduyla |
| [Semantic Segmentation with DeepLabV3](Applications/Building_AI_Solutions_with_Vitis_AI/Semantic_Segmentation_DeepLabV3_KV260/) | Kria KV260 | DPU üzerinde DeepLabV3 MobileNetV3 ile canlı kamera segmentasyonu, derlenmiş modeller ve betiklerle |

## Uçta yapay zeka

Uçta yapay zeka, eğitilmiş bir modeli doğrudan veriyi toplayan cihaz üzerinde çalıştırır. Bu cihaz bir kamera, bir sensör kartı ya da bir araç bilgisayarı olabilir. Veri bir bulut sunucusuna gidip geri dönmez, böylece sonuç tam ihtiyaç duyulan yerde elde edilir.

Bunun birkaç pratik faydası vardır:

- Ağ üzerinden gidiş dönüş olmadığı için düşük ve öngörülebilir gecikme
- Cihazdan ham video ya da sensör verisi yerine yalnızca sonuçlar çıktığı için daha az bant genişliği
- Veri cihazda kaldığı için daha iyi veri gizliliği
- Sürekli çalışan uygulamalarda daha düşük güç tüketimi ve maliyet

Zorluk, uç cihazların güç ve bellek kaynaklarının sınırlı olmasıdır. Modellerin daha küçük ve hızlı hale getirilmesi gerekir. Bu genellikle modeli 8 bitlik tam sayılara nicemleyerek yapılır ve sinir ağı çıkarımı için tasarlanmış bir donanım gerektirir.

## AMD Vitis

[AMD Vitis](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vitis.html), AMD adaptif SoC ve FPGA'lar üzerinde uygulama geliştirmek için kullanılan yazılım platformudur. Arm işlemciler için gömülü yazılımı, programlanabilir mantıkta donanım hızlandırmayı ve Versal cihazlardaki AI Engine'lerin programlanmasını kapsar.

[Vitis AI](https://www.amd.com/en/developer/resources/vitis-ai.html), bu platformun yapay zeka çıkarımına ayrılmış parçasıdır. PyTorch gibi bir çatıda eğitilmiş bir modeli alır, INT8'e nicemler (doğruluğun gerektirdiği yerlerde BF16 kullanır), hedef hızlandırıcı için derler ve cihaz üzerinde çalıştırır. Bu hızlandırıcı Zynq UltraScale+ ve Kria cihazlarda DPU, Versal AI Edge cihazlarda ise AI Engine tabanlı NPU'dur. Bu repository'deki Versal, Zynq UltraScale+ ve Kria demoları Vitis ve Vitis AI ile geliştirilmiştir.

## İletişim

Demolar ya da kaynak kodlarıyla ilgili sorularınız için: [ai@empa.com](mailto:ai@empa.com)

<sub>Ürün adları ilgili sahiplerinin ticari markalarıdır. Her uygulamanın kaynak kodu ve üçüncü taraf modelleri kendi lisansları kapsamında kullanılır.</sub>
