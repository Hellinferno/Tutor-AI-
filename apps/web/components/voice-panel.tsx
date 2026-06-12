"use client";

import { useState, useRef } from "react";
import { textToSpeech, speechToText, ApiError } from "../lib/api";

export function VoicePanel() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcription, setTranscription] = useState<string>("Click record to start dictation...");
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  async function handleRecord() {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" }); // Try webm first, or let STT handle it
        stream.getTracks().forEach((track) => track.stop());

        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64data = reader.result as string;
          const base64Audio = base64data.split(',')[1] || base64data;
          
          setBusy(true);
          setError(null);
          setTranscription("Processing...");
          try {
            // Using "webm" format since modern browsers typically record in webm or mp4
            const res = await speechToText(base64Audio, "webm");
            if (res.ok) {
              setTranscription(res.text);
            } else {
              setError(res.error || "STT failed");
              setTranscription("Failed to transcribe.");
            }
          } catch (err) {
            setError(err instanceof ApiError ? err.message : "Error connecting to STT service");
            setTranscription("Failed to transcribe.");
          } finally {
            setBusy(false);
          }
        };
      };

      mediaRecorder.start();
      setIsRecording(true);
      setTranscription("Recording...");
    } catch (err) {
      console.error(err);
      setError("Microphone access denied or unavailable.");
    }
  }

  async function handleSpeak() {
    const textToSay = transcription !== "Click record to start dictation..." && transcription !== "Processing..." && transcription !== "Recording..." && transcription !== "Failed to transcribe." 
      ? transcription 
      : "Hello from StudyLab. This is a voice output test.";
      
    setBusy(true);
    setError(null);
    try {
      const res = await textToSpeech(textToSay, "wav");
      if (res.ok) {
        setAudioSrc(`data:audio/wav;base64,${res.audio_base64}`);
      } else {
        setError(res.error || "TTS failed");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error connecting to TTS service");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" id="voice">
      <div className="panelHeader">
        <h3>Voice input / output</h3>
        <span className="badge">Gemini API</span>
      </div>
      <div className="voiceControls">
        <button type="button" className="voiceBtn" onClick={handleRecord} disabled={busy && !isRecording}>
          {isRecording ? "⏹ Stop recording" : "🎤 Start recording"}
        </button>
        <button type="button" className="voiceBtn" onClick={handleSpeak} disabled={busy || isRecording}>
          🔊 Speak answer
        </button>
      </div>
      
      {error && <small className="errorText">{error}</small>}
      
      <div className="voiceInput">
        <p className="eyebrow">Transcription</p>
        <div className="voiceResult">{transcription}</div>
      </div>
      <div className="voiceOutput">
        <p className="eyebrow">Synthesised audio</p>
        <div className="voiceResult">
          {audioSrc ? (
            <audio controls src={audioSrc} autoPlay />
          ) : (
            'Click "Speak answer" to hear output...'
          )}
        </div>
      </div>
      <p className="hint">
        Requires a Gemini API key set via <code>GEMINI_API_KEY</code>.
        Falls back to mock mode otherwise.
      </p>
    </section>
  );
}
