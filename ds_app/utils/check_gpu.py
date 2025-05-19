from pynvml import (
    nvmlInit,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetMemoryInfo,
    nvmlShutdown,
    NVMLError,
)
from loguru import logger


def check_gpu_memory(device=0, batch_size=30, decode_image=100):
    """
    Check if the GPU has sufficient free memory for the decoding process.

    Parameters:
        device (int): GPU device index (default is 0).
        batch_size (int): Number of images in a batch.
        decode_image (int): Memory required for decoding one image in MB.

    Returns:
        bool: True if there is enough GPU memory available; otherwise, raises an error.

    Raises:
        RuntimeError: If GPU memory is insufficient or if there is an error accessing the GPU device.
    """
    try:
        # Initialize NVML
        nvmlInit()

        # Get the handle for the specified GPU device
        handle = nvmlDeviceGetHandleByIndex(device)

        # Get memory information for the device
        mem_info = nvmlDeviceGetMemoryInfo(handle)
        # Calculate required VRAM for the decoding process (in bytes)
        vram_needed = batch_size * decode_image * 1024 ** 2  # Convert MB to bytes
        # Log GPU memory details
        logger.info(
            f"GPU device {device} info: "
            f"Total: {mem_info.total / 1024 ** 3:.3f} GB | "
            f"Free: {mem_info.free / 1024 ** 3:.3f} GB | "
            f"Used: {mem_info.used / 1024 ** 3:.3f} GB | "
            f"Required for decode: {vram_needed / 1024 ** 3:.3f} GB "
        )



        # Check if there is enough free GPU memory
        if mem_info.free >= vram_needed:
            return True
        else:
            raise RuntimeError(
                f"Not enough GPU memory for decoding. "
                f"Required: {vram_needed / 1024 ** 3:.3f} GB | "
                f"Available: {mem_info.free / 1024 ** 3:.3f} GB"
            )

    except NVMLError as e:
        raise RuntimeError(f"Error accessing GPU device {device}: {e}")

    finally:
        # Shutdown NVML to free resources
        nvmlShutdown()


# Example usage
if __name__ == "__main__":
    try:
        result = check_gpu_memory(device=0, batch_size=30, decode_image=100)
        if result:
            print("Sufficient GPU memory available.")
    except RuntimeError as error:
        print(error)