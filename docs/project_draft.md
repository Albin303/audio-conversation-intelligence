# AI-Based Sales Conversation Intelligence - Draft

## Project Overview

We developed an AI-based sales conversation intelligence system that can analyze customer conversations from text, uploaded audio, and live browser meeting recording. The system extracts important sales signals such as product interest, brand preference, budget, objections, customer hesitation, sentiment, and buying intent. Based on these signals, it predicts whether the customer lead is hot, warm, or cold.

The main goal of this project is to help sales teams understand customer behavior quickly and make better follow-up decisions.

## What We Did

We built a complete pipeline for analyzing sales conversations. The system accepts typed conversation text, uploaded audio files, and live browser meeting capture. If audio is uploaded or recorded, it is first converted into text. Then the conversation is analyzed using AI and NLP methods to extract useful features. These features are passed to a trained machine learning model to predict the conversion probability of the customer.

We also created a backend API and a frontend dashboard so users can upload audio, enter text, record a live meeting tab, view extracted features, check sentiment, and see the final lead prediction.

## Live Recording Feature

We added a live browser meeting capture feature in the frontend. This allows the user to click **Start Capture**, select a browser tab where the meeting is running, and capture the tab audio. The system also tries to capture the user's microphone so both the customer and sales person's voice can be included.

The recording is handled in the browser using the MediaRecorder API. Audio chunks are collected locally while the meeting is being captured. When the user clicks **Stop Capture**, the chunks are combined into one WebM audio file. This recorded file is then sent to the backend upload API.

After the recording reaches the backend, Whisper transcribes the recorded meeting audio into text. The generated transcript is then passed through the same sales intelligence pipeline: LLaMA extraction, sentiment analysis, feature engineering, XGBoost prediction, and final lead scoring.

This feature is useful because sales teams can analyze actual live meeting conversations instead of only manually typed text or previously saved audio files.

## Technologies Used

### Python
Python is used for the backend, AI processing, feature extraction, and machine learning logic. It is useful because it has strong support for AI, NLP, data processing, and model training.

### FastAPI
FastAPI is used to create the backend API. It receives text or audio from the frontend, processes the data, and sends the final analysis result back. It is fast, simple, and supports modern API development.

### Whisper
Whisper is used for speech-to-text transcription. When the user uploads an audio file, Whisper converts the speech into readable text so that the NLP pipeline can analyze it.

### Browser MediaRecorder API
The MediaRecorder API is used for live recording in the browser. It captures meeting tab audio and microphone audio, stores the audio as chunks, and creates a final WebM file for backend processing.

### getDisplayMedia and getUserMedia
getDisplayMedia is used to capture audio from the selected browser tab. getUserMedia is used to capture microphone input from the local user. Together, they help record both sides of a live sales meeting.

### LLaMA 3
LLaMA 3 is used to extract structured sales information from the conversation. It identifies important details like product, brand, budget, intent, urgency, objection, and decision stage.

### VADER Sentiment Analysis
VADER is used to calculate the sentiment score of the customer conversation. It helps identify whether the customer is positive, neutral, negative, hesitant, or emotionally engaged.

### XGBoost / Scikit-learn
XGBoost and Scikit-learn are used for machine learning-based lead conversion prediction. The trained model uses extracted features to calculate the probability of a customer converting.

### Pandas and NumPy
Pandas and NumPy are used for data handling, feature preparation, and model input formatting.

### Joblib
Joblib is used to save and load the trained machine learning model and feature list.

### Next.js, React, and TypeScript
Next.js with React and TypeScript is used for the frontend dashboard. It provides a modern user interface where users can upload audio, enter conversation text, view extracted signals, and see prediction results.

### Tailwind CSS
Tailwind CSS is used for frontend styling. It helps create a clean and responsive user interface.

### Axios
Axios is used in the frontend to communicate with the FastAPI backend.

### FFmpeg
FFmpeg supports audio processing and helps Whisper handle different audio file formats.

## Pipeline Working

1. The user enters sales conversation text, uploads an audio file, or starts live browser meeting capture.
2. For live capture, the browser records the selected meeting tab audio and microphone audio.
3. The recorded audio chunks are combined into a single WebM file after the user stops recording.
4. If audio is uploaded or recorded, Whisper converts the audio into text.
5. The text is sent to the FastAPI backend.
6. The system checks whether the conversation is relevant for sales analysis.
7. LLaMA 3 extracts structured sales features such as product, brand, budget, intent, urgency, objection, and decision stage.
8. VADER calculates the sentiment score from the conversation.
9. Additional features such as confidence score, hesitation score, delay flag, brand count, feature count, and interaction length are generated.
10. The semantic mapping layer normalizes extracted values into a format suitable for the model.
11. The trained XGBoost model predicts the base conversion probability.
12. A probability fusion layer combines model output, behavioral signals, intent score, emotion score, and engagement score.
13. The final output gives the lead label as hot, warm, or cold, along with probability and explanation reasons.
14. The frontend displays the transcript, extracted features, sentiment, conversion score, risk level, insights, and suggested next steps.

## Final Output

The system provides:

- Extracted sales features
- Live meeting transcript after recording
- Customer sentiment
- Buying intent
- Objections and hesitation signals
- Conversion probability
- Lead category: hot, warm, or cold
- Explanation reasons
- Suggested next actions for the sales team

## Conclusion

This project combines live browser recording, audio processing, natural language processing, large language models, machine learning, and a modern web dashboard. It helps convert raw sales conversations and live meeting recordings into useful business insights and supports sales teams in prioritizing leads and planning follow-ups.
