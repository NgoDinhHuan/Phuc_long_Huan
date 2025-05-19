import os
import requests

if __name__ == "__main__":
    video_path = "/app/test_volumes/evidence_output/7297170438710103_PAR02_2024-07-15_08:13:14.019507.mp4"
    prompt = """How many persons in this video?"""
    llava_url = "http://192.168.1.91:8089/videos/chat"
    data = {"query": prompt}
    headers = {"accept": "application/json"}
    files = {
        "file": (
            os.path.basename(video_path),
            open(video_path, "rb"),
            "video/mp4",
        )
    }
    response = None
    response = requests.post(llava_url, headers=headers, files=files, data=data)
    answer = response.json()["response"].lower()
    print(answer)
