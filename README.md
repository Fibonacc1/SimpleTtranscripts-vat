# Audio/Video Processor with Whisper GUI

## 🔄 Overview

A Python application with a graphical interface (Tkinter) for processing video and audio files:

* Extract audio from video (FFmpeg)
* Transcribe audio (OpenAI Whisper model)
* Full cycle: video → audio → text
* Visual log, progress bar, ability to stop processes

## 🛠️ Requirements

* **Python** 3.10+
* **FFmpeg** installed and available in `PATH`
* **PyTorch** with CUDA support (optional, for acceleration)
* **OpenAI Whisper**

## 📂 Project Structure

```
project/
  input/          # Source video files
  audio/          # Extracted audio files
  transcripts/    # Transcription text files
  output/         # Processing results (if any)
  go.bat          # Batch file to start the app
  run_whisper.py  # Script with GUI and processing logic
```

## 📝 Installation

1. Clone the repository:

```bash
git clone https://github.com/username/repo.git
cd repo
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate # macOS/Linux
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Make sure `ffmpeg` is installed and available in your PATH.

## 🔧 Launch

**Windows:**

* Double-click `go.bat`
* Or from the terminal:

```bash
python run_whisper.py
```

## 🕹️ Usage

1. Place video files in the `input/` folder
2. Launch the application
3. Select a mode:

   * *Extract audio* — saves the audio file in `audio/`
   * *Transcribe audio* — creates a `.txt` file in `transcripts/`
   * *Full cycle* — performs both steps
4. Logs and progress will be displayed in the interface

## 🛡️ License

Licensed under the Apache License, Version 2.0. You may not use this file except in compliance with the License. You may obtain a copy of the License at:

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
