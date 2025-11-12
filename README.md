🎬 Blobserk Video Tools
=======================

💻  Python ≥ 3.9 | Windows • macOS • Linux  
🔧  Requires FFmpeg + FFprobe  
📦  License: MIT  

------------------------------------------------------------
Split, preview & compress videos automatically — with animated progress ✨  
Perfect for creators, teachers, or archivists needing to upload long videos (Telegram, Drive, YouTube...) under 2 GB limits.
------------------------------------------------------------

🧠 Overview
------------

This project provides two complementary Python scripts:

| Script | Purpose | Typical Use |
|:-------|:---------|:-------------|
| blobserk.py | Split or re-encode a single video into parts ≤ 2 GB with animated console feedback | Individual large files |
| blobserkfolder.py | Batch process an entire folder (and subfolders) of videos automatically | Series, lectures, archives |

Both rely on FFmpeg for lossless cutting or optional re-encoding.  
No external Python libraries required — animations run entirely in the console.

------------------------------------------------------------
✨ Features
------------

✅ Estimate final file size before cutting  
✅ Automatic split into equal-sized parts (≤ 2 GB by default)  
✅ Optional re-encode for precise sizing / compression  
✅ Fancy console animations (spinner • snake • dots • earth • random)  
✅ Recursive folder processing & skip existing  
✅ Parallel jobs support (folder mode)  
✅ Cross-platform (Windows • macOS • Linux)

------------------------------------------------------------
⚙️ Installation
----------------

1️⃣ Install FFmpeg (includes ffmpeg + ffprobe)

• Windows  
    winget install Gyan.FFmpeg

• macOS  
    brew install ffmpeg

• Linux / Ubuntu  
    sudo apt update && sudo apt install ffmpeg -y

2️⃣ Clone or download this repository  
3️⃣ Run the scripts with Python ≥ 3.9

------------------------------------------------------------
🚀 Usage
--------

▶️ Single Video — blobserk.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Split a single file into multiple parts ≤ 2 GB:
    python blobserk.py "video.mp4" --size-limit 2G

Preview file size and number of parts before splitting:
    python blobserk.py "video.mp4" --simulate

Re-encode to control bitrate and file weight precisely:
    python blobserk.py "video.mp4" --reencode --video-bitrate 2500k --audio-bitrate 128k

------------------------------------------------------------
📁 Folder Mode — blobserkfolder.py
----------------------------------

Process an entire directory of videos (recursively or not):
    python blobserkfolder.py "D:\Videos" --size-limit 1900M

Run recursively and skip already-processed files:
    python blobserkfolder.py "D:\Videos" --recursive --skip-existing

Specify output root and use multiple threads:
    python blobserkfolder.py "D:\Videos" --outroot "D:\Splits" --jobs 4

------------------------------------------------------------
🧩 Options Summary
------------------

| Option | Applies to | Description |
|:--------|:------------|:-------------|
| --size-limit <value> | all | Max size per part (2G, 1900M...) |
| --outdir / --outroot | all | Output folder (default: ./splits) |
| --prefix | single | Custom file prefix |
| --simulate | single | Preview only |
| --reencode | single | Re-encode mode |
| --video-bitrate / --audio-bitrate | single | Target bitrates |
| --recursive | folder | Include subfolders |
| --skip-existing | folder | Skip already split |
| --jobs | folder | Parallel processes |

------------------------------------------------------------
🖼️ Example Output
-----------------

== Preview ==
Input: lecture.mp4  
Duration: 01:38:12  
Mode: stream copy (no re-encode)  
Estimated size: 4.11 GB  
Estimated parts: ~2  
Processing...
lecture_part01.mp4  (1.99 GB ≈ 49 min)  
lecture_part02.mp4  (2.01 GB ≈ 49 min)  
✓ Done!

------------------------------------------------------------
💡 Tips
-------

• For Telegram, keep each part under 2 GB.  
• Re-encoding compresses more but takes longer.  
• Combine with telegram-upload wrapper for automated uploads.  
• Works perfectly in scheduled tasks or background jobs.

------------------------------------------------------------
🧭 Roadmap
-----------

[ ] Live progress bar with speed indicator  
[ ] Telegram upload integration (animated)  
[ ] GUI drag-and-drop interface  

------------------------------------------------------------
🤝 Contributing
---------------

Pull requests welcome — animations, optimizations, or new features!  
Code style : Black (line length 100).  
Keep scripts dependency-free.

------------------------------------------------------------
💙 Credits
-----------

Made with love and pure Python  
© 2025 — Blobserk Video Tools by swyftos
