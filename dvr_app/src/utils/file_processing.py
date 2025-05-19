import re



def extract_video_duration_from_srs_config(config_file_path: str):
    dvr_duration = 60 # Default value
    with open(config_file_path, 'r') as file:
        config = file.read()

    # Use regular expression to match the dvr_duration
    match = re.search(r'dvr_duration\s+(\d+);', config)
    if match:
        dvr_duration = int(match.group(1))
    return dvr_duration
