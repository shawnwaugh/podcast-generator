# AI Podcast Generator

Type a topic and get a short podcast about it. Claude researches the topic on the web and writes a script for two hosts, Kyle and Samantha. ElevenLabs voices them, and the app stitches the result into one MP3 you can play or download.

Kyle is the dry, skeptical expert. Samantha is the enthusiastic big picture thinker who asks him to explain the jargon.

## How it works

1. Claude searches the web through DuckDuckGo, using at least two different queries, and writes a research summary under 500 words.
2. A second Claude call turns that summary into a script of alternating lines, one per host.
3. ElevenLabs reads each line in that host's voice.
4. pydub joins the lines into a single MP3.

The two prompts at the top of `app.py` (`system_prompt` and `podcast_prompt`) control the research behavior and the show format. Editing them is the fastest way to make the show your own.

## What you need

1. Python 3.10 or newer
2. ffmpeg, which pydub uses to handle MP3 files. On a Mac: `brew install ffmpeg`
3. An Anthropic API key
4. An ElevenLabs API key

## Run it locally

Replace YOUR_GITHUB_USERNAME with the account that hosts this repo.

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/podcast-generator.git
cd podcast-generator

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="paste your key here"
export ELEVENLABS_API_KEY="paste your key here"

streamlit run app.py
```

Streamlit prints a local address in the terminal. Open it in your browser.

The `export` lines last only for that terminal window. Your keys are never written into the code or the repo.

## Costs

Each podcast makes several Claude calls and one ElevenLabs call per line of dialogue. Both are billed to the keys you provide.

## Changing the voices

The voice IDs for Kyle and Samantha are set inside `generate_podcast_audio` in `app.py`. Replace them with any voice ID available to your ElevenLabs account.

## Docker

The included `Dockerfile` builds the same app, with ffmpeg installed, and serves it on port 8501. This is how the original Hugging Face Space runs it.

```bash
docker build -t podcast-generator .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY=your_key -e ELEVENLABS_API_KEY=your_key podcast-generator
```

## License

Apache 2.0. See the LICENSE file.
