#!/bin/bash
# Kria KV260 Face Recognition Deployment Script (Petalinux)
# Optimized for Petalinux environment


echo "=========================================="
echo "Kria KV260 Face Recognition Deployment"
echo "=========================================="

# Disable screen saver and power management
sudo xset s off
sudo xset -dpms

# Load DPU application
echo "Loading DPU application..."
sudo xmutil unloadapp
sudo xmutil loadapp kv260-smartcam
sleep 5
echo "✓ DPU application loaded"

# Setup Vitis AI environment (Petalinux paths)
echo ""
echo "Setting up Vitis AI environment..."

# Source Vitis AI setup if available (Petalinux location may differ)
if [ -f /opt/xilinx/vitis_ai_library/setup.sh ]; then
    source /opt/xilinx/vitis_ai_library/setup.sh
    echo "✓ Vitis AI environment loaded"
elif [ -f /usr/share/vitis_ai_library/setup.sh ]; then
    source /usr/share/vitis_ai_library/setup.sh
    echo "✓ Vitis AI environment loaded"
else
    echo "Note: Vitis AI setup script not found (typical for Petalinux)"
fi

# Set DPU environment variables for optimal performance
export XLNX_ENABLE_CACHE=1
export XLNX_ENABLE_FINGERPRINT_CHECK=0
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1

# # Disable CPU frequency scaling for consistent performance
# if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
#     echo "Setting CPU governor to performance mode..."
#     sudo sh -c 'echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor' 2>/dev/null || true
#     sudo sh -c 'echo performance > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor' 2>/dev/null || true
#     sudo sh -c 'echo performance > /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor' 2>/dev/null || true
#     sudo sh -c 'echo performance > /sys/devices/system/cpu/cpu3/cpufreq/scaling_governor' 2>/dev/null || true
#     echo "✓ CPU governor set to performance"
# fi

# Run face recognition application
echo ""
echo "Starting face recognition application..."
echo ""

# # Run with optimal CPU affinity and priority
# if [ "$EUID" -eq 0 ] || sudo -n true 2>/dev/null; then
#     # Running as root or passwordless sudo available
#     echo "Running with elevated priority (nice -20)..."
#     sudo nice -n -20 taskset -c 0,1 sudo -u $USER python3 app_facerecognition_generic.py
# else
#     # No sudo access - run with normal priority
#     echo "Running with normal priority..."
#     taskset -c 0,1 python3 app_facerecognition_generic.py
# fi

HEIGHT=600
WIDTH=800

xrandr -s ${WIDTH}x${HEIGHT}

python3 app_video_DeepLabV3_MobilenetV3.py 
echo ""
echo "Application finished!"
