# AI Podcast Generator
# Flow: Claude researches a topic with a web search tool loop, a second Claude
# call turns the summary into a two host script, ElevenLabs voices each line,
# and pydub joins the lines into one MP3.
# Requires ANTHROPIC_API_KEY and ELEVENLABS_API_KEY as environment variables,
# and ffmpeg installed on the machine.

import streamlit as st
import anthropic
import json
import os
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from ddgs import DDGS

# --- Page Setup ---
st.set_page_config(page_title="AI Podcast Generator", page_icon="🎙️")
st.title("🎙️ AI Podcast Generator")
st.write("Listen to a custom podcast about anything you can imagine.")

# --- Session State Initialization ---
if "podcast_audio" not in st.session_state:
    st.session_state.podcast_audio = None
    st.session_state.podcast_filename = None
    st.session_state.podcast_script = None

# --- API Keys ---
anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")

if not anthropic_key:
    st.error("No Anthropic API key found. Please set ANTHROPIC_API_KEY.")
    st.stop()
if not elevenlabs_key:
    st.error("No ElevenLabs API key found. Please set ELEVENLABS_API_KEY.")
    st.stop()

claude_client = anthropic.Anthropic(api_key=anthropic_key)
elevenlabs_client = ElevenLabs(api_key=elevenlabs_key)

# --- Prompts ---
system_prompt = """You are a research assistant. When given a topic, your job is to 
search for information and produce a well-organized summary. Follow these rules:

1. SEARCHING: Always perform at least 2 different searches using different angles 
   or keywords before writing your summary. Cast a wide net.

2. EVALUATE RESULTS: If a search returns irrelevant or low-quality results, try 
   a different query. Don't use bad results just because they're there.

3. OUTPUT FORMAT: Structure your final summary as:
   - A one-paragraph overview of the topic
   - 3-5 key findings, each as a short paragraph
   - A "What to watch" section noting open questions or emerging trends

4. TONE: Write for a smart non-expert. Avoid jargon. If you must use a technical 
   term, explain it in parentheses.

5. HONESTY: If your search results are thin on a subtopic, say so. Never make up 
   facts or present your general knowledge as if it came from the search results.

6. LENGTH: Keep the total summary under 500 words. Be concise."""

podcast_prompt = """You are writing a script for two podcast hosts.

Kyle — skeptical, dry, asks sharp questions, a real know-it-all who isn't afraid to show it.
Samantha — enthusiastic, big-picture thinker, loves tangents.

Rules:
- Kyle opens the conversation.
- Each host speaks for 2-3 sentences per turn.
- Go for 4 rounds each.
- Kyle speaks like an expert. Samantha explains technical jargon in plain language 
  and asks for clarification or elaboration.
- Use filler words, filled pauses, and hesitation markers to mimic the rhythm of a real conversation.
- Avoid m-dashes, markdown, asterisks, and other punctuation that cannot be spoken by TTS.
- End with a "What to watch" closing from Kyle.
- Format each line as: Kyle: or Samantha: followed by their dialog."""

# --- Tools ---
tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information on a topic. Use this when you need to find facts, recent developments, or information you don't already know.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                }
            },
            "required": ["query"]
        }
    }
]

def run_search(search_query):
    try:
        results = DDGS().text(search_query, max_results=5)
        if not results:
            return "No results found for this query."
        output = ""
        for result in results:
            output += f"Title: {result['title']}\n"
            output += f"Snippet: {result['body']}\n\n"
        return output
    except Exception as error:
        return f"Search failed with error: {error}"

# --- Audio Generation ---
def generate_podcast_audio(podcast_text, output_filename):
    kyle_voice = "4YYIPFl9wE5c4L2eu2Gb"
    samantha_voice = "mWqiTfcp72MprLxlUR8h"

    lines = podcast_text.strip().split("\n")
    combined_audio = AudioSegment.empty()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Kyle:"):
            selected_voice = kyle_voice
            dialog = line.replace("Kyle:", "").strip()
        elif line.startswith("Samantha:"):
            selected_voice = samantha_voice
            dialog = line.replace("Samantha:", "").strip()
        else:
            continue

        generated_audio = elevenlabs_client.text_to_speech.convert(
            text=dialog,
            voice_id=selected_voice,
            model_id="eleven_turbo_v4_turbo",
            output_format="mp3_44100_128",
        )

        audio_bytes = b""
        for chunk in generated_audio:
            audio_bytes += chunk

        temp_file = "temp_line.mp3"
        with open(temp_file, "wb") as file:
            file.write(audio_bytes)
        segment = AudioSegment.from_mp3(temp_file)
        combined_audio += segment
        os.remove(temp_file)

    combined_audio.export(output_filename, format="mp3")

# --- Main App ---
topic = st.text_input("What would you like to research?", placeholder="e.g. The future of AI agents in business")

if st.button("Generate Podcast") and topic:

    # Research
    status = st.status("Researching your topic...", expanded=True)
    messages = [{"role": "user", "content": topic}]

    max_loops = 5
    research_summary = ""

    for i in range(max_loops):
        response = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            for item in response.content:
                if hasattr(item, "text"):
                    research_summary += item.text
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for item in response.content:
                if item.type == "tool_use":
                    search_query = item.input["query"]
                    status.write(f"🔍 Searching: {search_query}")
                    search_results = run_search(search_query)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": item.id,
                        "content": search_results
                    })

            messages.append({"role": "user", "content": tool_results})

    status.update(label="Research complete!", state="complete")

    # Generate podcast script
    with st.status("Writing podcast script...", expanded=False):
        podcast_response = claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=podcast_prompt,
            messages=[
                {"role": "user", "content": f"Turn this research into a podcast conversation:\n\n{research_summary}"}
            ]
        )

        podcast_text = ""
        for item in podcast_response.content:
            if hasattr(item, "text"):
                podcast_text += item.text

    # Store the script in Session State
    st.session_state.podcast_script = podcast_text

    # Generate audio
    with st.status("Generating audio...", expanded=False):
        safe_topic = topic.replace(" ", "_").replace("?", "").replace("/", "").replace(":", "")[:50]
        filename_mp3 = f"podcast_{safe_topic}.mp3"

        generate_podcast_audio(podcast_text, filename_mp3)

    # Store audio in Session State
    with open(filename_mp3, "rb") as audio_file:
        st.session_state.podcast_audio = audio_file.read()
        st.session_state.podcast_filename = filename_mp3

    # Clean up the file from disk since it is now stored in memory
    os.remove(filename_mp3)

# --- Display podcast if one exists in Session State ---
if st.session_state.podcast_audio:
    st.subheader("🎧 Listen")
    st.audio(st.session_state.podcast_audio, format="audio/mp3")
    st.download_button(
        label="⬇️ Download Full Podcast",
        data=st.session_state.podcast_audio,
        file_name=st.session_state.podcast_filename,
        mime="audio/mp3"
    )