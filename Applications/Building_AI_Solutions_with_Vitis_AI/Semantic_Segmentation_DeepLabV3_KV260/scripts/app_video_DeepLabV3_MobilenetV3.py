"""

    DeepLabV3 MobileNetV3 Video Application using Vitis-AI Library
    ----------------------------------------------------------------
    This script captures video from a webcam or file, processes each frame using a DeepLabV3 semantic segmentation model,
    and visualizes the segmentation results in real-time. The model is loaded from an xmodel file, and the
    output is blended with the original frame for visualization. The script also displays the frames per second (FPS)
    for both the visualizer and the DPU processing.
    
    How to Run:
        ./configure.sh
        python3 app_video_DeepLabV3_MobileNetV3.py

    Requirements:
        - Installed accelerator for DPU execution (kv260-benchmark-b4096) 
        - Vitis AI Ubuntu Python environment (pre-installed with Vitis AI Library)
        - The required xmodel file exists at the specified path.
        - Using the correct video source path for cv2.VideoCapture(0). Replace with a filename for video file input.

    Author:      Empa AI / Empa Ar-Ge
    Date:        July 2025
    Contact:     ai@empa.com

    Versions:
    - DeepLabV3_MobileNetV3.xmodel for standard model
    - OUT_H, OUT_W = 520, 520 for default model input dimensions

"""

# REQUIRED MODULES
import xir
import vitis_ai_library
import numpy as np
import cv2
import time
import threading
from queue import Queue
import yaml
import os

# Load configuration from YAML file
script_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(script_dir, "config.yaml")
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# DEFINITIONS - Load from config
# Camera settings
CAM_W = config['camera']['width']
CAM_H = config['camera']['height']
CAM_DEVICE = config['camera']['device']
CAM_FRAMERATE = config['camera']['framerate']
CAM_BUFFER_SIZE = config['camera']['buffer_size']

# Display settings
OUT_W = config['display']['width']
OUT_H = config['display']['height']
name_visualization_window = config['display']['window_name']
DISPLAY_FULLSCREEN = config['display']['fullscreen']

# Model settings
OUT_W_MODEL = config['model']['input_width']
OUT_H_MODEL = config['model']['input_height']
MODEL_ARCH = config['model']['architecture']
DPU_VERSION = config['model']['dpu_version']

# Visualization settings
BLEND_ALPHA = config['visualization']['blend_alpha']
BLEND_BETA = config['visualization']['blend_beta']
LIST_COLORS_ARRAY = np.array(config['visualization']['colors'], dtype=np.uint8)
COLOR_OVERLAY = tuple(config['visualization']['overlay_color'])
OVERLAY_ALPHA = config['visualization']['overlay_alpha']
CLASS_NAMES = config['visualization']['class_names']

# Color definitions for consistent styling
COLOR_TEXT = (255, 255, 255)  # White text

class GuiAdder:
    def __init__(self, resize_to=(640,480)):
        self.resize_to = resize_to
        self.font_scale = self.resize_to[1] / 1200
        self.font_scale_model_name = self.resize_to[1] / 600
        self.font_thickness = max(1, int(self.resize_to[1] / 700))
        self.font = cv2.FONT_HERSHEY_DUPLEX
        # Load logo with absolute path to ensure it works from any directory
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "empa.png")
        self.logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
        if self.logo is None:
            print(f"Warning: Could not load logo from {logo_path}")
        # LOWER BLACK BAR
        self.bar_height_percentage = 0.125
        self.bar_height = int(self.resize_to[1] * self.bar_height_percentage)
        self.bar_y_start = self.resize_to[1] - self.bar_height
        self.text_y_start = self.bar_y_start + int(0.25 * self.bar_height)
        self.text_spacing = int(self.bar_height / 4)
        self.text_x = self.resize_to[0] - 150  # Right side - adjusted for DeepLabV3 text
        self.model_name_text = f"Semantic Segmentation"
        (self.text_width, self.text_height), _ = cv2.getTextSize(self.model_name_text, self.font, self.font_scale_model_name, self.font_thickness)
        self.fps_x = (self.resize_to[0] - self.text_width) // 2
        self.fps_y = self.bar_y_start + (self.bar_height + self.text_height) // 2
        if self.logo is not None:
            self.logo_height, self.logo_width = self.logo.shape[:2]
            self.scale_factor = self.resize_to[1] / 1300
            self.resized_logo = cv2.resize(self.logo, (int(self.logo_width * self.scale_factor), int(self.logo_height * self.scale_factor)))
            self.logo_y_offset = self.bar_y_start + (self.bar_height - self.resized_logo.shape[0]) // 2
            self.logo_x_offset = 5
            self.bgr_logo = self.resized_logo[:, :, :3]
            self.alpha_logo = self.resized_logo[:, :, 3] / 255.0
        else:
            self.resized_logo = None
            
    def __call__(self, im_unpad):
        im_unpad = cv2.resize(im_unpad, self.resize_to, interpolation=cv2.INTER_LINEAR)
        im_unpad[self.bar_y_start:, :, :] = (im_unpad[self.bar_y_start:, :, :] * 0.5).astype(np.uint8)
        
        # Add performance metrics on the right side (matching face recognition layout)
        bar_offset_y = 15
        cv2.putText(im_unpad, "DeepLabV3", (self.text_x, self.text_y_start + bar_offset_y), self.font, self.font_scale, (70, 182, 98), self.font_thickness, cv2.LINE_AA)
        cv2.putText(im_unpad, "MobileNetV3", (self.text_x, self.text_y_start + self.text_spacing + bar_offset_y), self.font, self.font_scale, (70, 182, 98), self.font_thickness, cv2.LINE_AA)
        
        # Add model name in center
        cv2.putText(im_unpad, self.model_name_text, (self.fps_x, self.fps_y), self.font, self.font_scale_model_name, (255, 255, 255), self.font_thickness, cv2.LINE_AA)
        
        # Add the logo dynamically (if logo is available)
        if self.resized_logo is not None:
            roi = im_unpad[self.logo_y_offset:self.logo_y_offset + self.resized_logo.shape[0], self.logo_x_offset:self.logo_x_offset + self.resized_logo.shape[1]]
            for c in range(3):
                roi[:, :, c] = (1 - self.alpha_logo) * roi[:, :, c] + self.alpha_logo * self.bgr_logo[:, :, c]
        
        return im_unpad


# capture source
def get_camera_pipeline():
    """
    Create GStreamer pipeline for camera capture with multiple format fallbacks
    """
    # Try different formats in order of preference
    pipelines = [
        # Try USB camera with MJPEG format (most common and efficient)
        f"v4l2src device={CAM_DEVICE} ! video/x-raw,format=YUY2,width={CAM_W},height={CAM_H},framerate={CAM_FRAMERATE}/1 ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1",
        # Fallback to auto-negotiated format
        f"v4l2src device={CAM_DEVICE} ! videoconvert ! video/x-raw,format=BGR ! appsink drop=1",
        # Simple fallback
        f"v4l2src device={CAM_DEVICE} ! videoconvert ! appsink"
    ]
    return pipelines

def test_camera_source():
    """
    Test different camera sources and return the working one
    """
    pipelines = get_camera_pipeline()
    
    # First try GStreamer pipelines
    for i, pipeline in enumerate(pipelines):
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    cap.release()
                    return pipeline, cv2.CAP_GSTREAMER
                cap.release()
        except:
            pass
    
    # Fallback to regular webcam
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                cap.release()
                return 0, cv2.CAP_ANY
        cap.release()
    except:
        pass
    
    return None, None

class CameraCapture:
    """
    Threaded camera capture class for improved frame rate and reduced latency
    """
    def __init__(self, src, backend, buffer_size=2):
        self.capture = cv2.VideoCapture(src, backend)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce internal buffer
        self.q = Queue(maxsize=buffer_size)
        self.running = False
        self.thread = None
        
    def start(self):
        """Start the frame capture thread"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._capture_frames)
        self.thread.daemon = True
        self.thread.start()
        return self
        
    def _capture_frames(self):
        """Internal method to capture frames in a separate thread"""
        while self.running:
            ret, frame = self.capture.read()
            if not ret:
                self.running = False
                break
                
            # If queue is full, remove oldest frame
            if self.q.full():
                try:
                    self.q.get_nowait()
                except:
                    pass
            
            # Add new frame to queue
            try:
                self.q.put(frame, block=False)
            except:
                pass  # Queue full, skip frame
                
    def read(self):
        """Read the latest frame from the queue"""
        if not self.q.empty():
            frame = self.q.get()
            return True, frame
        return False, None
        
    def stop(self):
        """Stop the capture thread and release resources"""
        self.running = False
        if self.thread is not None:
            self.thread.join()
        self.capture.release()
        
    def isOpened(self):
        """Check if capture is opened"""
        return self.capture.isOpened()

# Print initialization banner
print("\n" + "="*60)
print(" DeepLabV3 MobileNetV3 - Semantic Segmentation")
print("="*60)

# Test and select the best capture source
print("[1/7] Testing camera sources...")
CAPTURE_SOURCE, CAPTURE_BACKEND = test_camera_source()
if CAPTURE_SOURCE is None:
    print("      ✗ ERROR: No working camera source found")
    exit(1)
print(f"      ✓ Camera initialized: {CAM_W}x{CAM_H}@{CAM_FRAMERATE}fps")

# Define xmodel path
path_model = f"/home/ubuntu/Vitis-AI/DEV/models/pt_segmentation_DeepLabV3/model_compiled/DeepLabV3_MobileNetV3_{OUT_H_MODEL}_{MODEL_ARCH}_{DPU_VERSION}.xmodel"

if MODEL_ARCH == "Hybrid":
    MODEL_ARCH = "Hybrid (DPU+CPU)"

print(f"\n[2/7] Loading model ({MODEL_ARCH} ({DPU_VERSION}))...")
try:
    graph = xir.Graph.deserialize(path_model)
    print(f"      ✓ Model loaded: {os.path.basename(path_model)}")
except Exception as e:
    print(f"      ✗ ERROR: Failed to load model - {e}")
    exit(1)

print("\n[3/7] Creating DPU runner...")
dpu_runner = vitis_ai_library.GraphRunner.create_graph_runner(graph)
print("      ✓ DPU runner created")

print("\n[4/7] Configuring tensors...")
list_input_tensor_buffers = dpu_runner.get_inputs()
list_output_tensor_buffers = dpu_runner.get_outputs()

list_input_shapes = [inp_tens.get_tensor().dims for inp_tens in list_input_tensor_buffers]
list_output_shapes = [out_tens.get_tensor().dims for out_tens in list_output_tensor_buffers]
print(f"      ✓ Input: {list_input_shapes[0]}, Output: {list_output_shapes[0]}")

fixpos = list_input_tensor_buffers[0].get_tensor().get_attr("fix_point")
scaler_input = 2**fixpos

list_output_data = []
for shape in list_output_shapes:
    array = np.empty((shape), dtype=np.float32)
    array = array.transpose(0,3,1,2)
    list_output_data.append(array)

print("\n[5/7] Initializing camera capture...")

threaded_camera = CameraCapture(CAPTURE_SOURCE, CAPTURE_BACKEND, buffer_size=CAM_BUFFER_SIZE)
if not threaded_camera.isOpened():
    print("      ✗ ERROR: Could not open video capture")
    exit(1)
threaded_camera.start()
time.sleep(0.5)  # Brief wait for camera warmup
print("      ✓ Camera capture started")

print("\n[6/7] Setting up visualization...")
add_gui = GuiAdder((OUT_W, OUT_H))
if DISPLAY_FULLSCREEN:
    cv2.namedWindow(name_visualization_window, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(name_visualization_window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    print(f"      ✓ Display: {OUT_W}x{OUT_H} (fullscreen)")
else:
    cv2.namedWindow(name_visualization_window, cv2.WINDOW_AUTOSIZE)
    print(f"      ✓ Display: {OUT_W}x{OUT_H} (windowed)")

print("\n[7/7] Starting inference loop...")
print("      ✓ Ready! Press 'q' to quit\n")
print("="*60)
while(True):
    # Measure time for each frame processing
    t1 = time.time()

    # Step-8) read frame from threaded video capture
    ret, frame = threaded_camera.read()
    if not ret or frame is None or frame.size == 0:
        # Skip this iteration if no frame available
        time.sleep(0.01)  # Small delay to prevent busy waiting
        continue
    # Step-9) Pre-process the frame
    # Convert frame from BGR to RGB, resize, normalize
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Resize frame to match model input size
    frame = cv2.resize(frame, (OUT_W_MODEL, OUT_H_MODEL))
    # Normalize frames using ImageNet mean and std
    frame_norm = ((frame / 255.0 - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)).astype(np.float32)
    # Put the frame into the input tensor buffer & scale it
    list_input_data = []
    list_input_data.append((frame_norm * scaler_input).astype(np.int8))
    # Measure DPU processing start time
    tdpu1 = time.time()
    # Step-10) Run graph runner instance
    job_id = dpu_runner.execute_async(list_input_data, list_output_data)
    dpu_runner.wait(job_id)
    # Measure DPU processing end time
    tdpu2 = time.time()
    # POST-PROCESSING: get predictions from output buffer, then process it for visualization.
    # Get the first output (assuming single output)
    out = list_output_data[0]
    # Get the predicted classes by taking the argmax along the channel dimension
    # Output shape is [batch, channels, height, width], we need argmax along channels (axis=1)
    predicted_classes = np.argmax(out, axis=1).squeeze()
    # Convert predicted classes to colors for visualization
    colored_segmentation = LIST_COLORS_ARRAY[predicted_classes]
    # Convert frame back to BGR for visualization
    image_to_visualize = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    # Blend the original image with the colored segmentation using config weights
    blended_image = (BLEND_ALPHA * image_to_visualize.astype(np.float32) + 
                     BLEND_BETA * colored_segmentation.astype(np.float32))
    # Convert blended image to uint8 for visualization
    blended_image_np = blended_image.astype(np.uint8)
    # Compute FPS values
    t2 = time.time()
    fps = 1 / round(t2 - t1, 4) if (t2 - t1) > 0 else 0
    fps_dpu = 1 / round(tdpu2 - tdpu1, 4) if (tdpu2 - tdpu1) > 0 else 0
    
    # Get unique detected classes (excluding background)
    unique_classes = np.unique(predicted_classes)
    detected_classes = [int(cls) for cls in unique_classes if cls > 0]  # Exclude background (0)
    
    # Apply GUI styling exactly like face recognition
    img_gui = add_gui(blended_image_np)
    
    # Prepare info board text lines
    info_lines = [
        f"FPS: {round(fps)}",
        f"Input Size: {OUT_W_MODEL}x{OUT_H_MODEL}",
        f"Model Type: {MODEL_ARCH} ({DPU_VERSION})",
        f"DPU: {round(fps_dpu)} fps, {(tdpu2-tdpu1)*1000:.1f}ms"
    ]
    
    # Calculate adaptive overlay dimensions based on text
    font_face = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.45
    font_thickness = 1
    padding = 5
    line_spacing = 22
    
    # Get maximum text width
    max_text_width = 0
    for line in info_lines:
        (text_width, text_height), _ = cv2.getTextSize(line, font_face, font_scale, font_thickness)
        max_text_width = max(max_text_width, text_width)
    
    # Calculate overlay size
    info_w = max_text_width + 2 * padding
    info_h = len(info_lines) * line_spacing + padding
    
    # Add top-left overlay for performance info with adaptive size
    overlay = img_gui.copy()
    cv2.rectangle(overlay, (0, 0), (info_w, info_h), tuple(config['visualization']['overlay_background']), -1)
    cv2.addWeighted(overlay, OVERLAY_ALPHA, img_gui, 1 - OVERLAY_ALPHA, 0, img_gui)
    
    # Add performance metrics (restructured format)
    for i, line in enumerate(info_lines):
        y_pos = padding + (i + 1) * line_spacing - 5
        cv2.putText(img_gui, line, (padding, y_pos), font_face, font_scale, COLOR_OVERLAY, font_thickness, cv2.LINE_AA)
    
    # Add top-right overlay for detected classes
    if detected_classes:
        # Calculate overlay dimensions based on number of classes
        class_h = min(len(detected_classes) * 22 + 30, 400)  # Max height limit
        class_w = 180
        class_x = img_gui.shape[1] - class_w
        
        overlay_classes = img_gui.copy()
        cv2.rectangle(overlay_classes, (class_x, 0), (class_x + class_w, class_h), 
                     tuple(config['visualization']['overlay_background']), -1)
        cv2.addWeighted(overlay_classes, OVERLAY_ALPHA, img_gui, 1 - OVERLAY_ALPHA, 0, img_gui)
        
        # Add title
        cv2.putText(img_gui, "Detected:", (class_x + 5, 20), cv2.FONT_HERSHEY_DUPLEX, 0.5, COLOR_OVERLAY, 1, cv2.LINE_AA)
        
        # Add detected class names line by line
        for i, cls_id in enumerate(detected_classes[:15]):  # Limit to 15 classes
            if cls_id < len(CLASS_NAMES):
                class_name = CLASS_NAMES[cls_id]
                y_pos = 45 + i * 22
                # Draw colored box indicator
                color = tuple([int(c) for c in LIST_COLORS_ARRAY[cls_id]])
                cv2.rectangle(img_gui, (class_x + 5, y_pos - 12), (class_x + 18, y_pos), color, -1)
                cv2.rectangle(img_gui, (class_x + 5, y_pos - 12), (class_x + 18, y_pos), (255, 255, 255), 1)
                # Draw class name
                cv2.putText(img_gui, class_name, (class_x + 23, y_pos), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imshow(name_visualization_window, img_gui)
    
    # Exit condition: press 'q' to quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

print("\n" + "="*60)
print("Shutting down...")
threaded_camera.stop()
cv2.destroyAllWindows()
print("✓ Resources released. Goodbye!")
print("="*60 + "\n")
