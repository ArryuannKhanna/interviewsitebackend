import base64
import json
from channels.generic.websocket import AsyncWebsocketConsumer
# import whisper  # Assuming Whisper is installed
# import redis
import requests
import os
import google.generativeai as genai
# from redis import Redis
import redis.asyncio as redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)


class VideoCallConsumer(AsyncWebsocketConsumer):
    os.environ['API_KEY'] = 'AIzaSyC-alNfZfEDq2a9j2-GcZ1y7KcMZf6plp8'
    genai.configure(api_key=os.environ['API_KEY'])
    model1 = genai.GenerativeModel('gemini-1.5-flash')
    prompt_initial = '''You are a technical interviewer who would evaluate the candidate strictly on questions related 
                    to based on the skills mentioned in the user's resume and the job description.Ask only
                     most commonly asked questions. Always start with asking candidate to introduce themselves.'''
    prompt_cross = '''Based on the following interaction history,don't comment on the accuracy of the
                     answer, just ask the next relevant question-'''
    prompt_cross_ext = '''If you feel there is no further cross question. Then consider asking the next question with the following info.'''
    prompt_resume = "resume-"
    prompt_job_description = "job desrcription-"
    prompt_previous_asked_questions = "This is the summary of topics you have asked thus far-"
    history_prompt = "Make summary of the following asked question-"
    greet_prompt = "Firstly greet the candidate and then ask your first question."

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'video_call_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await redis_client.hset("hello", mapping={
            "resume": "",
            "job_description": "",
            "interactions": json.dumps([]),  # Store all questions and responses
            "interaction_history": ""
        })

        await self.accept()



    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'audio':
            audio_file_path = "temp_audio.webm"
            try:
                # Decode Base64 audio data
                audio_data = base64.b64decode(data['audioData'])
                print("Audio data decoded successfully!")

                # Save WebM audio file
                with open(audio_file_path, "wb") as f:
                    f.write(audio_data)

                # Verify file size
                if os.path.getsize(audio_file_path) == 0:
                    print("Error: Uploaded file is empty.")
                    await self.send(text_data=json.dumps({'error': 'Uploaded file is empty'}))
                    return

                # Send audio to Flask server for transcription
                flask_url = "https://7e6d-35-243-200-252.ngrok-free.app/transcribe"
                with open(audio_file_path, "rb") as audio_file:
                    print("Sending WebM audio to Flask...")
                    response = requests.post(flask_url, files={'file': audio_file})

                # Handle Flask response
                if response.status_code == 200:
                    transcription = response.json().get('transcription', 'No transcription received')
                    print(f"Transcription: {transcription}")

                    # Retrieve and update interactions from Redis
                    interactions = json.loads(await redis_client.hget(self.room_group_name, "interactions") or "[]")

                    if interactions and interactions[-1]["answer"] is None:
                        # Update the last unanswered question with the answer
                        interactions[-1]["answer"] = transcription

                    # Save updated interactions back to Redis
                    await redis_client.hset(self.room_group_name, "interactions", json.dumps(interactions))

                    # Send transcription back to the client
                    await self.send(text_data=json.dumps({
                        'transcription': transcription,
                        'message': "Transcription received successfully.",
                    }))

                    # Retrieve the last interaction and include it in the next question prompt
                    interaction_history = json.dumps(interactions, indent=2)
                    resume_info = (await redis_client.hget(self.room_group_name, "resume") or b"").decode("utf-8")
                    job_description = (await redis_client.hget(self.room_group_name, "job_description") or b"").decode("utf-8")
                    interaction_summary = (await redis_client.hget(self.room_group_name, "interaction_history") or b"").decode("utf-8")

                    prompt = self.prompt_cross + interaction_history + self.prompt_cross_ext + self.prompt_resume + resume_info + self.prompt_job_description + job_description + self.prompt_previous_asked_questions + interaction_summary
                    response = self.model1.generate_content(prompt)

                    final_history_prompt = self.history_prompt + response.text

                    response1 = self.model1.generate_content(final_history_prompt)

                    interaction_history_updated = interaction_summary + response1.text

                    await redis_client.hset(self.room_group_name, "interaction_history", interaction_history_updated)

                    # Add the new question to the interactions
                    interactions.append({"question": response.text, "answer": None})
                    await redis_client.hset(self.room_group_name, "interactions", json.dumps(interactions))

                    # Send the next question to the client
                    await self.send(text_data=json.dumps({
                        'message': response.text
                    }))
                else:
                    # Handle errors from Flask server
                    error_message = response.json().get('error', 'Unknown error from Flask server')
                    print(f"Error from Flask: {error_message}")
                    await self.send(text_data=json.dumps({'error': error_message}))

            except Exception as e:
                print(f"Exception occurred: {e}")
                await self.send(text_data=json.dumps({'error': str(e)}))

            finally:
                # Clean up the temporary audio file
                if os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    print("Temporary audio file removed.")

        elif data.get('type') == 'job_info':
            resume_info = data['resume']
            job_description = data['jobDescription']

            await redis_client.hset(self.room_group_name, "resume", resume_info)
            await redis_client.hset(self.room_group_name, "job_description", job_description)

            final_prompt = self.prompt_initial + self.prompt_resume + resume_info + self.prompt_job_description + job_description + self.greet_prompt

            response = self.model1.generate_content(final_prompt)

            final_history_prompt = self.history_prompt + response.text

            response1 = self.model1.generate_content(final_history_prompt)

            interaction_history = await redis_client.hget(self.room_group_name,"interaction_history")
            interaction_history_str = interaction_history.decode("utf-8") if interaction_history else ""
            interaction_history_updated = interaction_history_str + response1.text

            await redis_client.hset(self.room_group_name,"interaction_history",interaction_history_updated)

            # Save the initial question to interactions in Redis
            interactions = json.loads(await redis_client.hget(self.room_group_name, "interactions") or "[]")
            interactions.append({"question": response.text, "answer": None})
            await redis_client.hset(self.room_group_name, "interactions", json.dumps(interactions))

            # Send the initial question to the client
            await self.send(text_data=json.dumps({
                'message': response.text
            }))
        elif data.get('type') == 'code_data':
            transcription = data['code']
            interactions = json.loads(await redis_client.hget(self.room_group_name, "interactions") or "[]")

            if interactions and interactions[-1]["answer"] is None:
                # Update the last unanswered question with the answer
                interactions[-1]["answer"] = transcription

            # Save updated interactions back to Redis
            await redis_client.hset(self.room_group_name, "interactions", json.dumps(interactions))

            # Send transcription back to the client
            await self.send(text_data=json.dumps({
                'transcription': transcription,
                'message': "Transcription received successfully.",
            }))

            # Retrieve the last interaction and include it in the next question prompt
            interaction_history = json.dumps(interactions, indent=2)
            resume_info = (await redis_client.hget(self.room_group_name, "resume") or b"").decode("utf-8")
            job_description = (await redis_client.hget(self.room_group_name, "job_description") or b"").decode("utf-8")
            interaction_summary = (await redis_client.hget(self.room_group_name, "interaction_history") or b"").decode(
                "utf-8")

            prompt = self.prompt_cross + interaction_history + self.prompt_cross_ext + self.prompt_resume + resume_info + self.prompt_job_description + job_description + self.prompt_previous_asked_questions + interaction_summary
            response = self.model1.generate_content(prompt)

            final_history_prompt = self.history_prompt + response.text

            response1 = self.model1.generate_content(final_history_prompt)

            interaction_history_updated = interaction_summary + response1.text

            await redis_client.hset(self.room_group_name, "interaction_history", interaction_history_updated)

            # Add the new question to the interactions
            interactions.append({"question": response.text, "answer": None})
            await redis_client.hset(self.room_group_name, "interactions", json.dumps(interactions))

            # Send the next question to the client
            await self.send(text_data=json.dumps({
                'message': response.text
            }))
        else:
            # Handle chat messages
            pass
