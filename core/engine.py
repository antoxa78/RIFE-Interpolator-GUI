import os
import torch
import numpy as np
from core.model.IFNet import IFNet

if torch.cuda.is_available():
    torch.backends.cudnn.enabled = True
    torch.backends.cudnn.benchmark = True

def _check_torch_compile():
    if not torch.cuda.is_available():
        return False
    try:
        dummy = torch.nn.Linear(1, 1)
        compiled = torch.compile(dummy, mode="reduce-overhead")
        compiled(torch.randn(1, 1))
        return True
    except Exception:
        return False

TORCH_COMPILE_AVAILABLE = _check_torch_compile()


class InferenceEngine:
    def __init__(self, checkpoint_path=None, device=None, fp16=False, compile_model=False):
        self.device = device if device else self._auto_device()
        self._fp16 = fp16 and self.device.type == 'cuda'
        self._compile = compile_model and TORCH_COMPILE_AVAILABLE and self.device.type == 'cuda'
        self.flownet = None
        self._compiled_flownet = None
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.load_model(checkpoint_path)

    @property
    def compile_enabled(self):
        return self._compile

    @compile_enabled.setter
    def compile_enabled(self, value):
        value = bool(value) and TORCH_COMPILE_AVAILABLE and self.device.type == 'cuda'
        if self._compile != value:
            self._compile = value
            self._compiled_flownet = None

    @property
    def fp16(self):
        return self._fp16

    @fp16.setter
    def fp16(self, value):
        value = bool(value) and self.device.type == 'cuda'
        if self._fp16 != value:
            self._fp16 = value
            if self.flownet is not None:
                if value:
                    self.flownet.half()
                else:
                    self.flownet.float()
                self._compiled_flownet = None

    @staticmethod
    def _auto_device():
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    @property
    def device_info(self):
        if self.device.type == "cuda":
            name = torch.cuda.get_device_name(0)
            cap = torch.cuda.get_device_capability(0)
            mem_total = torch.cuda.get_device_properties(0).total_memory // (1024**2)
            cc_num = cap[0] * 10 + cap[1]

            fp16_supported = cc_num >= 53
            has_tensor_cores = cc_num >= 70
            fp16_recommended = cc_num >= 80

            if fp16_recommended:
                fp16_note = "FP16: 2x speed (Tensor Cores)"
            elif has_tensor_cores:
                fp16_note = "FP16: supported, limited gain"
            elif fp16_supported:
                fp16_note = "FP16: supported, no speedup"
            else:
                fp16_note = "FP16: unsupported"

            return {
                "type": "cuda",
                "name": name,
                "compute": f"{cap[0]}.{cap[1]}",
                "cc_num": cc_num,
                "memory_mb": mem_total,
                "fp16": self.fp16,
                "fp16_supported": fp16_supported,
                "fp16_recommended": fp16_recommended,
                "fp16_note": fp16_note,
                "summary": f"{name} ({mem_total} MB)"
            }
        elif self.device.type == "mps":
            return {
                "type": "mps",
                "name": "Apple Metal",
                "compute": "n/a",
                "memory_mb": 0,
                "fp16": False,
                "summary": "Apple Metal (MPS)"
            }
        else:
            return {
                "type": "cpu",
                "name": "CPU",
                "compute": "n/a",
                "memory_mb": 0,
                "fp16": False,
                "summary": "CPU only"
            }

    def load_model(self, checkpoint_path):
        state = torch.load(checkpoint_path, map_location=self.device)
        state = {k.replace("module.", ""): v for k, v in state.items() if "module." in k} or state

        self.flownet = IFNet()
        self.flownet.load_state_dict(state)
        self.flownet.to(self.device)

        if self._fp16:
            self.flownet.half()
        self.flownet.eval()

        # CUDA warmup (also triggers lazy torch.compile if enabled)
        if self.device.type == 'cuda':
            with torch.no_grad():
                dummy = torch.randn(1, 6, 128, 128, device=self.device)
                if self._fp16:
                    dummy = dummy.half()
                self._active_flownet(dummy, [4, 2, 1])
            torch.cuda.synchronize()

    def unload_model(self):
        self.flownet = None
        self._compiled_flownet = None
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()

    @property
    def is_loaded(self):
        return self.flownet is not None

    @property
    def _active_flownet(self):
        if self._compile and self._compiled_flownet is None:
            try:
                self._compiled_flownet = torch.compile(self.flownet, mode="reduce-overhead")
            except Exception:
                self._compile = False
                self._compiled_flownet = None
        if self._compiled_flownet is not None:
            return self._compiled_flownet
        return self.flownet

    def _pad_to_multiple(self, img, multiple=32):
        h, w = img.shape[2], img.shape[3]
        pad_h = (multiple - h % multiple) % multiple
        pad_w = (multiple - w % multiple) % multiple
        if pad_h == 0 and pad_w == 0:
            return img, (0, 0, 0, 0)
        return torch.nn.functional.pad(img, (0, pad_w, 0, pad_h), mode='replicate'), (pad_h, pad_w, h, w)

    def _unpad(self, img, pad_info):
        pad_h, pad_w, h, w = pad_info
        if pad_h == 0 and pad_w == 0:
            return img
        return img[:, :, :h, :w]

    def _to_tensor(self, frame_np):
        frame = torch.from_numpy(np.ascontiguousarray(frame_np)).float().to(self.device) / 255.0
        frame = frame.permute(2, 0, 1).unsqueeze(0)
        if self._fp16:
            frame = frame.half()
        return frame

    def _from_tensor(self, tensor):
        tensor = tensor.clamp(0, 1).squeeze(0).permute(1, 2, 0)
        if self._fp16:
            tensor = tensor.float()
        return (tensor.cpu().numpy() * 255).astype(np.uint8)

    def inference_image_pair(self, img0_np, img1_np, scale=1.0, TTA=False):
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        img0 = self._to_tensor(img0_np)
        img1 = self._to_tensor(img1_np)

        img0, pad_info = self._pad_to_multiple(img0)
        img1, _ = self._pad_to_multiple(img1)

        imgs = torch.cat((img0, img1), 1)
        scale_list = [4.0 / scale, 2.0 / scale, 1.0 / scale]

        with torch.no_grad():
            _, _, merged, _, _, _ = self._active_flownet(imgs, scale_list)
            result = merged[2]
            if TTA:
                with torch.no_grad():
                    imgs_flip = torch.cat((img0.flip(2).flip(3), img1.flip(2).flip(3)), 1)
                    _, _, merged2, _, _, _ = self._active_flownet(imgs_flip, scale_list)
                result = (result + merged2[2].flip(2).flip(3)) / 2

        result = self._unpad(result, pad_info)
        return self._from_tensor(result)

    def inference_image_pair_batch(self, img0_np, img1_np, timesteps, scale=1.0, TTA=False):
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")

        img0 = self._to_tensor(img0_np)
        img1 = self._to_tensor(img1_np)

        img0, pad_info = self._pad_to_multiple(img0)
        img1, _ = self._pad_to_multiple(img1)

        imgs = torch.cat((img0, img1), 1)
        scale_list = [4.0 / scale, 2.0 / scale, 1.0 / scale]

        results = []
        with torch.no_grad():
            for t in timesteps:
                _, _, merged, _, _, _ = self._active_flownet(imgs, scale_list, timestep=t)
                result = merged[2]
                if TTA:
                    with torch.no_grad():
                        imgs_flip = torch.cat((img0.flip(2).flip(3), img1.flip(2).flip(3)), 1)
                        _, _, merged2, _, _, _ = self._active_flownet(imgs_flip, scale_list, timestep=t)
                    result = (result + merged2[2].flip(2).flip(3)) / 2
                result = self._unpad(result, pad_info)
                results.append(self._from_tensor(result))

        return results
