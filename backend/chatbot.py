"""Fitness Q&A with an optional server-side OpenAI adapter and local fallback."""
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def reply(message):
    text = message.lower()
    if any(x in text for x in ("diagnos", "medicine", "medication", "injury", "pain", "disease")):
        return "I can share general fitness information, but I can’t diagnose or advise on medication. For symptoms, injury, or a health condition, contact a qualified healthcare professional."
    if "beginner" in text or "workout" in text or "exercise" in text:
        return "A gentle starting point is 2–3 short full-body sessions each week: sit-to-stands, wall push-ups, hip hinges, and easy walking. Begin comfortably, rest between sessions, and build gradually. Adapt exercises to your ability."
    if "vegetarian" in text or "meal" in text or "food" in text:
        return "For a balanced vegetarian meal, pair lentils, beans, tofu, or yogurt with vegetables and a grain such as rice or oats. Choose portions that suit your appetite and preferences. Check labels for allergens."
    if "track" in text or "progress" in text or "consistent" in text or "routine" in text:
        return "Choose a realistic time and minimum session length, then record the date, activity, duration, and how it felt. Review your weekly pattern rather than expecting every day to go perfectly."
    return "Start with a manageable routine you enjoy: regular walks, two or three weekly strength sessions, enough rest, and varied meals. Progress gradually and adjust for your ability. I can offer general information, not medical advice."


def chat_reply(message):
    # Keep medical-risk topics local and only share the current question with AI.
    if any(x in message.lower() for x in ("diagnos", "medicine", "medication", "injury", "pain", "disease")):
        return {"reply": reply(message), "source": "rule_based"}
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        return {"reply": reply(message), "source": "rule_based"}
    payload={"model":os.getenv("OPENAI_MODEL","gpt-4o-mini"),"messages":[
        {"role":"developer","content":"You are a general fitness information assistant. Give concise, practical, conservative guidance. Do not diagnose, prescribe medication, provide individualized medical nutrition treatment, or claim to replace a qualified healthcare professional. For symptoms, injuries, medical conditions, pregnancy, or medication questions, tell the user to consult a qualified healthcare professional. Do not recommend extreme calorie restriction or unsafe exercise."},
        {"role":"user","content":message}],"max_completion_tokens":300,"store":False}
    req=Request("https://api.openai.com/v1/chat/completions",data=json.dumps(payload).encode("utf-8"),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=12) as response: data=json.loads(response.read(1_000_000))
        content=data["choices"][0]["message"]["content"]
        if isinstance(content,str) and content.strip():return {"reply":content.strip(),"source":"openai"}
    except (HTTPError,URLError,TimeoutError,KeyError,IndexError,ValueError,OSError):
        pass
    return {"reply":reply(message),"source":"rule_based","note":"The optional AI service was unavailable; this is a local rule-based response."}
