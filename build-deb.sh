#!/bin/bash
set -e

APP_NAME="rife-interpolator"
VERSION="1.1.2"
ARCH="amd64"
PKG_NAME="${APP_NAME}_${VERSION}_${ARCH}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="/tmp/${APP_NAME}-build"
PKG_DIR="${BUILD_DIR}/${PKG_NAME}"

echo "Building ${APP_NAME} ${VERSION} (${ARCH})..."

rm -rf "$BUILD_DIR"

mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/opt/${APP_NAME}/checkpoints"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${PKG_DIR}/usr/share/doc/${APP_NAME}"

cp "$SCRIPT_DIR/main.py" "${PKG_DIR}/opt/${APP_NAME}/"
cp "$SCRIPT_DIR/requirements.txt" "${PKG_DIR}/opt/${APP_NAME}/"
cp -r "$SCRIPT_DIR/core" "${PKG_DIR}/opt/${APP_NAME}/"
cp -r "$SCRIPT_DIR/gui" "${PKG_DIR}/opt/${APP_NAME}/"
cp -r "$SCRIPT_DIR/utils" "${PKG_DIR}/opt/${APP_NAME}/"

find "${PKG_DIR}" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "${PKG_DIR}" -name '*.pyc' -delete 2>/dev/null || true

# Inject build timestamp and version
BUILD_DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
cat > "${PKG_DIR}/opt/${APP_NAME}/gui/dialogs/build_info.py" << BUILDEOF
VERSION = "${VERSION}"
BUILD_DATE = "${BUILD_DATE}"
BUILDEOF

cat > "${PKG_DIR}/DEBIAN/control" << 'CONTROL'
Package: rife-interpolator
Version: 1.1.2
Architecture: amd64
Maintainer: RIFE Interpolator Team
Depends: python3 (>= 3.10), python3-venv, python3-pip, python3-dev, ffmpeg
Recommends: nvidia-driver | mesa-opencl-icd
Section: video
Priority: optional
Homepage: https://github.com/hzwer/ECCV2022-RIFE
Description: Real-Time Intermediate Flow Estimation frame interpolator
 RIFE Interpolator is a desktop GUI application for video frame
 interpolation using the ECCV 2022 RIFE model. It supports
 2x-64x frame rate upscaling with real-time preview, arbitrary
 timestep interpolation, and batch processing.
 .
 Powered by PyTorch, PySide6, and the IFNet optical flow model.
CONTROL

cat > "${PKG_DIR}/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

# Update icon cache so the app icon shows in menus
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache /usr/share/icons/hicolor > /dev/null 2>&1 || true
fi

echo "RIFE Interpolator installed."
echo ""
echo "Python dependencies (torch, PySide6, etc.) will be"
echo "installed automatically on first launch."
echo ""
echo "  rife-interpolator"
echo ""
echo "Or find it in: Menu > Sound & Video > RIFE Interpolator"
POSTINST

cat > "${PKG_DIR}/DEBIAN/prerm" << 'PRERM'
#!/bin/bash
set -e

echo "RIFE Interpolator: removing..."
echo ""
echo "Note: Python venv and downloaded models remain in"
echo "  ~/.local/share/rife-interpolator/"
echo "Remove manually to free disk space if needed."
PRERM

cat > "${PKG_DIR}/usr/bin/${APP_NAME}" << 'WRAPPER'
#!/bin/bash
APP_DIR="/opt/rife-interpolator"
USER_DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/rife-interpolator"
VENV_DIR="$USER_DATA_DIR/venv"
STAMP_FILE="$VENV_DIR/.deps-installed"

if [ ! -d "$VENV_DIR" ]; then
    mkdir -p "$USER_DATA_DIR"
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

detect_gpu() {
    if lspci 2>/dev/null | grep -qi "nvidia" && command -v nvidia-smi &>/dev/null; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
        CUDA_VER=$(nvidia-smi 2>/dev/null | grep -oP "CUDA Version: \K[0-9.]+" | head -1)
        if [ -n "$CUDA_VER" ]; then
            echo "nvidia|${GPU_NAME}|${CUDA_VER}"
            return
        fi
    fi
    if lspci 2>/dev/null | grep -qi "nvidia"; then
        echo "nvidia|NVIDIA GPU (driver-only)|none"
        return
    fi
    if lspci 2>/dev/null | grep -qi "amd" && command -v rocminfo &>/dev/null; then
        echo "amd|AMD GPU (ROCm)|rocm"
        return
    fi
    if lspci 2>/dev/null | grep -qi "amd"; then
        echo "amd|AMD GPU (no ROCm)|none"
        return
    fi
    if lspci 2>/dev/null | grep -qi "intel"; then
        echo "intel|Intel Integrated|none"
        return
    fi
    echo "none|No GPU detected|none"
}

GPUVAL=$(detect_gpu)
GPU_TYPE=$(echo "$GPUVAL" | cut -d'|' -f1)
GPU_NAME=$(echo "$GPUVAL" | cut -d'|' -f2)
GPU_CUDA=$(echo "$GPUVAL" | cut -d'|' -f3)

if [ ! -f "$STAMP_FILE" ]; then
    if command -v zenity &> /dev/null; then
        # Stage 1: core deps (fast)
        echo "10"
        echo "# Updating pip..."
        "$VENV_DIR/bin/pip" install --upgrade pip -q 2>&1

        echo "15"
        echo "# Installing GUI framework..."
        "$VENV_DIR/bin/pip" install PySide6 -q 2>&1

        echo "25"
        echo "# Installing OpenCV, numpy, and tools..."
        "$VENV_DIR/bin/pip" install numpy opencv-python gdown requests -q 2>&1

        # Stage 2: PyTorch (large, GPU-aware)
        if [ "$GPU_TYPE" = "nvidia" ] && [ "$GPU_CUDA" != "none" ]; then
            CUDA_MAJOR=$(echo "$GPU_CUDA" | cut -d'.' -f1)
            CUDA_MINOR=$(echo "$GPU_CUDA" | cut -d'.' -f2)
            CUDA_VER_NUM=$((CUDA_MAJOR * 100 + CUDA_MINOR))
            # Map to nearest supported PyTorch CUDA build
            if [ "$CUDA_VER_NUM" -ge 126 ]; then
                CUDA_TAG="cu126"
            elif [ "$CUDA_VER_NUM" -ge 124 ]; then
                CUDA_TAG="cu124"
            elif [ "$CUDA_VER_NUM" -ge 121 ]; then
                CUDA_TAG="cu121"
            else
                CUDA_TAG="cu118"
            fi
            echo "30"
            echo "# NVIDIA GPU detected: ${GPU_NAME}"
            echo "# Installing PyTorch with CUDA ${GPU_CUDA}..."
            "$VENV_DIR/bin/pip" install torch torchvision --index-url "https://download.pytorch.org/whl/${CUDA_TAG}" -q 2>&1
        else
            echo "30"
            echo "# Installing PyTorch (CPU)..."
            "$VENV_DIR/bin/pip" install torch torchvision -q 2>&1
        fi

        echo "80"
        echo "# Verifying installation..."
        # Quick GPU verification
        if "$VENV_DIR/bin/python3" -c "import torch; print(torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
            echo "100"
            echo "# GPU support verified!"
        else
            echo "100"
            echo "# Running in CPU mode"
        fi

        touch "$STAMP_FILE"
        sleep 0.5
    else
        echo "RIFE Interpolator: first run setup..."
        echo "Installing dependencies (this may take a few minutes)..."
        "$VENV_DIR/bin/pip" install --upgrade pip -q 2>&1
        "$VENV_DIR/bin/pip" install PySide6 -q 2>&1
        "$VENV_DIR/bin/pip" install numpy opencv-python gdown requests -q 2>&1
        if [ "$GPU_TYPE" = "nvidia" ] && [ "$GPU_CUDA" != "none" ]; then
            CUDA_MAJOR=$(echo "$GPU_CUDA" | cut -d'.' -f1)
            CUDA_MINOR=$(echo "$GPU_CUDA" | cut -d'.' -f2)
            CUDA_VER_NUM=$((CUDA_MAJOR * 100 + CUDA_MINOR))
            if [ "$CUDA_VER_NUM" -ge 126 ]; then CUDA_TAG="cu126"
            elif [ "$CUDA_VER_NUM" -ge 124 ]; then CUDA_TAG="cu124"
            elif [ "$CUDA_VER_NUM" -ge 121 ]; then CUDA_TAG="cu121"
            else CUDA_TAG="cu118"; fi
            echo "Installing CUDA PyTorch for ${GPU_NAME}..."
            "$VENV_DIR/bin/pip" install torch torchvision --index-url "https://download.pytorch.org/whl/${CUDA_TAG}" 2>&1
        else
            echo "Installing CPU PyTorch..."
            "$VENV_DIR/bin/pip" install torch torchvision 2>&1
        fi
        touch "$STAMP_FILE"
        echo "Setup complete."
    fi
fi

cd "$APP_DIR"
exec "$VENV_DIR/bin/python3" main.py "$@"
WRAPPER

cat > "${PKG_DIR}/usr/share/applications/${APP_NAME}.desktop" << 'DESKTOP'
[Desktop Entry]
Name=RIFE Interpolator
Comment=Real-Time Frame Interpolation GUI
Exec=rife-interpolator
Icon=rife-interpolator
Terminal=false
Type=Application
Categories=AudioVideo;Video;
Keywords=frame;interpolation;rife;video;slow-motion;slo-mo;
StartupNotify=true
DESKTOP

python3 << 'PYEOF'
from PIL import Image, ImageDraw

size = 256
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

for r in range(size // 2, 0, -1):
    ratio = r / (size // 2)
    gray = int(30 + 25 * ratio)
    draw.ellipse(
        [size // 2 - r, size // 2 - r, size // 2 + r, size // 2 + r],
        fill=(gray, gray, gray, 255)
    )

ring_outer = size // 2 - 6
ring_inner = size // 2 - 14
for y in range(size):
    for x in range(size):
        dx = x - size // 2
        dy = y - size // 2
        dist = (dx * dx + dy * dy) ** 0.5
        if ring_inner <= dist <= ring_outer:
            progress = (dist - ring_inner) / (ring_outer - ring_inner)
            r = int(70 + 130 * progress)
            g = int(130 + 90 * progress)
            b = int(220 + 35 * progress)
            img.putpixel((x, y), (r, g, b, 255))

frame_w, frame_h = 56, 42
frame_y = size // 2 - frame_h // 2
left_x = 40
right_x = size - 40 - frame_w

draw.rectangle(
    [left_x, frame_y, left_x + frame_w, frame_y + frame_h],
    fill=(40, 40, 50, 200), outline=(100, 160, 240, 255), width=3
)
tri_points = [
    (left_x + frame_w // 2 - 8, frame_y + frame_h // 2 - 10),
    (left_x + frame_w // 2 - 8, frame_y + frame_h // 2 + 10),
    (left_x + frame_w // 2 + 10, frame_y + frame_h // 2),
]
draw.polygon(tri_points, fill=(100, 160, 240, 200))

draw.rectangle(
    [right_x, frame_y, right_x + frame_w, frame_y + frame_h],
    fill=(40, 40, 50, 200), outline=(100, 160, 240, 255), width=3
)
tri_points_r = [
    (right_x + frame_w // 2 - 8, frame_y + frame_h // 2 - 10),
    (right_x + frame_w // 2 - 8, frame_y + frame_h // 2 + 10),
    (right_x + frame_w // 2 + 10, frame_y + frame_h // 2),
]
draw.polygon(tri_points_r, fill=(100, 160, 240, 200))

arrow_y = size // 2
arrow_start_x = left_x + frame_w + 10
arrow_end_x = right_x - 10
draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)], fill=(100, 160, 240, 255), width=4)
arrow_size = 10
draw.polygon([
    (arrow_end_x, arrow_y),
    (arrow_end_x - arrow_size, arrow_y - arrow_size // 2),
    (arrow_end_x - arrow_size, arrow_y + arrow_size // 2),
], fill=(100, 160, 240, 255))

plus_size = 4
for i in range(1, 4):
    cx = int(arrow_start_x + i * (arrow_end_x - arrow_start_x) / 5)
    cy = arrow_y - 14
    draw.rectangle([cx - plus_size, cy - 1, cx + plus_size, cy + 1], fill=(160, 200, 255, 120))
    draw.rectangle([cx - 1, cy - plus_size, cx + 1, cy + plus_size], fill=(160, 200, 255, 120))

import os
icon_dir = os.environ.get('ICON_DIR', '/tmp/rife-build-icon')
os.makedirs(icon_dir, exist_ok=True)
img.save(os.path.join(icon_dir, 'rife-interpolator.png'))
PYEOF

cp /tmp/rife-build-icon/rife-interpolator.png "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

cat > "${PKG_DIR}/usr/share/doc/${APP_NAME}/copyright" << 'COPYRIGHT'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: rife-interpolator
Source: https://github.com/hzwer/ECCV2022-RIFE

Files: *
Copyright: 2022 Huang, Zhewei and Zhang, Tianyuan and Heng, Wen and Shi, Boxin and Zhou, Shuchang
License: MIT

Files: debian/*
Copyright: 2026 RIFE Interpolator GUI
License: MIT

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a
 copy of this software and associated documentation files (the "Software"),
 to deal in the Software without restriction, including without limitation
 the rights to use, copy, modify, merge, publish, distribute, sublicense,
 and/or sell copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
COPYRIGHT

chmod 755 "${PKG_DIR}/DEBIAN/postinst"
chmod 755 "${PKG_DIR}/DEBIAN/prerm"
chmod 755 "${PKG_DIR}/usr/bin/${APP_NAME}"

dpkg-deb --root-owner-group --build "$PKG_DIR"

DEB_FILE="${BUILD_DIR}/${PKG_NAME}.deb"
cp "$DEB_FILE" "$SCRIPT_DIR/"
rm -rf "$BUILD_DIR"

echo ""
echo "Done: $SCRIPT_DIR/${PKG_NAME}.deb"
echo "Size: $(du -h "$SCRIPT_DIR/${PKG_NAME}.deb" | cut -f1)"
echo ""
echo "Install: sudo apt install ./${PKG_NAME}.deb"
