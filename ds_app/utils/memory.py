import psutil


def is_memory_exceeded(threshold=0.8):
    """
    Check if the current memory usage of a container exceeds the given threshold.

    :param threshold: Percentage of memory usage to check against (default: 80%)
    :return: True if memory usage exceeds the threshold, False otherwise.
    """
    try:
        # Paths to cgroup memory stats
        memory_usage_path = "/sys/fs/cgroup/memory.current"
        memory_limit_path = "/sys/fs/cgroup/memory.max"

        # Read current memory usage
        with open(memory_usage_path, 'r') as usage_file:
            memory_usage = usage_file.read().strip()
            memory_usage = int(memory_usage)

        # Read memory limit
        with open(memory_limit_path, 'r') as limit_file:
            memory_limit = limit_file.read().strip()
            if memory_limit == "max":
                memory_limit = psutil.virtual_memory().total
            else:
                memory_limit = int(memory_limit)

        usage_percentage = float(memory_usage) / float(memory_limit)
        return usage_percentage > threshold
    except FileNotFoundError:
        raise EnvironmentError("Cgroup memory stats not found. Are you running inside a container?")
    except Exception as e:
        raise RuntimeError(f"An error occurred while checking memory usage: {e}")