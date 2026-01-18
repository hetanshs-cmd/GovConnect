import requests
import json
import os
from typing import List, Dict, Optional
from config import LLM_PROVIDER, LLM_DEFAULT_MODEL, LLM_API_URL, LLM_API_KEY

# =========================
# ENHANCED LLM CONFIG
# =========================

# LLM provider configuration (driven by environment via `config.py`)
# Defaults: provider=huggingface, model=gpt-5-mini
PRIMARY_MODEL = LLM_DEFAULT_MODEL
FALLBACK_MODEL = None

def _get_provider_headers():
    if LLM_PROVIDER == 'openai':
        return {
            'Authorization': f'Bearer {LLM_API_KEY}',
            'Content-Type': 'application/json'
        }
    # Default to HuggingFace style headers
    return {
        'Authorization': f'Bearer {LLM_API_KEY}' if LLM_API_KEY else '',
        'Content-Type': 'application/json'
    }

def _get_provider_url(model_name: str):
    if LLM_API_URL:
        return LLM_API_URL
    if LLM_PROVIDER == 'openai':
        return 'https://api.openai.com/v1/chat/completions'
    # huggingface inference endpoint
    return f'https://api-inference.huggingface.co/models/{model_name}'

# Conversation memory
conversation_history: Dict[str, List[Dict[str, str]]] = {}

# =========================
# ENHANCED CONTEXT
# =========================

GOVCONNECT_CONTEXT = """
You are GovConnect Assistant, a friendly and helpful AI helper for India's National Digital Public Services Platform, like a knowledgeable friend on a phone call.

SERVICES AVAILABLE:
1. HEALTHCARE SERVICES:
   - Book doctor appointments at government hospitals
   - Access public health information and advisories
   - Register new hospitals (admin only)
   - View healthcare statistics and KPIs

2. AGRICULTURE SERVICES:
   - Farmer registration and management
   - Crop monitoring and yield prediction
   - Weather forecasts and pest alerts
   - Irrigation scheduling and water management
   - Agricultural subsidies and scheme information

3. URBAN SERVICES:
   - Report civic issues (roads, water, electricity)
   - Track complaint status and resolution
   - Access municipal services and information
   - View infrastructure health metrics

4. SYSTEM FEATURES:
   - Real-time alerts and notifications
   - Dynamic database management for admins
   - User role management (Super Admin, Healthcare Admin, Agriculture Admin)
   - API health monitoring and system status

RESPONSE STYLE:
- Be friendly, conversational, and approachable, like talking to a helpful friend on the phone
- Use natural language: "Sure thing!", "I'd be happy to help!", "Let me guide you through that"
- Ask follow-up questions to better assist users
- Show enthusiasm and willingness to help
- Keep responses conversational but informative
- Use contractions and friendly phrases
- If something is unclear, ask for clarification in a friendly way
- End responses with offers for more help when appropriate
- Politely decline topics outside government services scope and redirect to relevant help
"""

# =========================
# ENHANCED CHATBOT FUNCTION
# =========================

def get_chatbot_response(user_message: str, user_id: str = "default") -> str:
    """Get enhanced AI-powered response with conversation memory"""
    try:
        # Initialize conversation history if needed
        if user_id not in conversation_history:
            conversation_history[user_id] = []

        # Add user message to history
        conversation_history[user_id].append({"role": "user", "content": user_message})

        # Keep only last 10 messages for context
        if len(conversation_history[user_id]) > 10:
            conversation_history[user_id] = conversation_history[user_id][-10:]

        # Try primary model first
        response = _call_llm_api(user_message, user_id, "primary")

        if response:
            # Add bot response to history
            conversation_history[user_id].append({"role": "assistant", "content": response})
            return response

        # Try fallback model
        response = _call_llm_api(user_message, user_id, "fallback")

        if response:
            conversation_history[user_id].append({"role": "assistant", "content": response})
            return response

        # If both models fail, use enhanced rule-based response
        return get_enhanced_rule_response(user_message, user_id)

    except Exception as e:
        print(f"Error in enhanced LLM: {e}")
        return get_enhanced_rule_response(user_message, user_id)

def _call_llm_api(user_message: str, user_id: str, model_type: str) -> Optional[str]:
    """Call LLM API with enhanced context"""
    try:
        # Build conversation context
        context_messages = conversation_history[user_id][-5:] if user_id in conversation_history else []

        # Create enhanced prompt text for providers that expect a single string
        system_prompt = f"{GOVCONNECT_CONTEXT}\n\nConversation History:\n"
        for msg in context_messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            system_prompt += f"{role}: {msg['content']}\n"

        # Decide provider and call accordingly
        headers = _get_provider_headers()
        model_name = PRIMARY_MODEL
        provider_url = _get_provider_url(model_name)

        if LLM_PROVIDER == 'openai':
            # OpenAI Chat Completions style
            messages = [
                {"role": "system", "content": GOVCONNECT_CONTEXT}
            ]
            # append recent conversation messages
            for msg in context_messages:
                role = 'user' if msg['role'] == 'user' else 'assistant'
                messages.append({"role": role, "content": msg['content']})
            messages.append({"role": "user", "content": user_message})

            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 250,
                "temperature": 0.7
            }

            response = requests.post(provider_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            choice = result.get('choices', [{}])[0]
            content = choice.get('message', {}).get('content') if isinstance(choice, dict) else None
            if content and len(content) > 5:
                return content.strip()

        else:
            # Default: HuggingFace Inference style (single prompt string)
            full_prompt = f"{system_prompt}\nUser: {user_message}\nAssistant:"
            payload = {
                "inputs": full_prompt,
                "parameters": {
                    "max_length": 200,
                    "min_length": 20,
                    "do_sample": True,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "repetition_penalty": 1.2,
                    "num_return_sequences": 1
                }
            }

            response = requests.post(provider_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()

            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get("generated_text", "")
                if "Assistant:" in generated_text:
                    response_text = generated_text.split("Assistant:")[-1].strip()
                    response_text = response_text.split("\nUser:")[0].strip()
                    if response_text and len(response_text) > 10:
                        return response_text

        return None

    except Exception as e:
        print(f"Error calling {model_type} model: {e}")
        return None

def is_out_of_scope(user_message: str) -> bool:
    """Check if the query is completely outside GovConnect's scope"""
    user_msg = user_message.lower()

    # Keywords that indicate out-of-scope topics
    out_of_scope_keywords = [
        # Entertainment & Media
        "movie", "film", "music", "song", "game", "gaming", "entertainment", "netflix", "youtube", "social media",
        # Shopping & Commerce (non-government)
        "shopping", "buy", "purchase", "store", "market", "ecommerce", "amazon", "flipkart",
        # Personal Finance (non-government)
        "bank", "loan", "credit card", "investment", "stock", "crypto", "bitcoin", "trading",
        # Travel & Transportation (non-government)
        "flight", "hotel", "booking", "travel", "vacation", "taxi", "uber", "ola",
        # Education (non-government)
        "school", "college", "university", "exam", "study", "course", "online learning",
        # Technology (general, non-government)
        "computer", "phone", "mobile", "laptop", "software", "programming", "coding",
        # Food & Dining
        "restaurant", "food", "recipe", "cooking", "dining",
        # Sports & Recreation
        "sports", "football", "cricket", "tennis", "gym", "fitness",
        # Personal Services
        "beauty", "salon", "spa", "laundry", "cleaning",
        # Real Estate (non-government)
        "property", "house", "apartment", "rent", "real estate",
        # Legal (non-government)
        "lawyer", "court", "legal", "divorce", "marriage",
        # Weather (general, not agriculture-specific)
        "weather"  # Note: weather is handled in agriculture context
    ]

    # Check for out-of-scope keywords
    for keyword in out_of_scope_keywords:
        if keyword in user_msg:
            return True

    # Check for questions about unrelated topics
    unrelated_patterns = [
        "what is", "how does", "explain", "tell me about", "who is",
        "when was", "where is", "why does", "how much", "how many"
    ]

    # If it contains question words and no government-related keywords, likely out of scope
    question_words = ["what", "how", "why", "when", "where", "who", "which", "can you"]
    gov_keywords = ["health", "medical", "hospital", "doctor", "farm", "agriculture", "farmer", "crop",
                   "urban", "civic", "complaint", "infrastructure", "admin", "system", "api", "government", "gov"]

    has_question = any(word in user_msg for word in question_words)
    has_gov_topic = any(word in user_msg for word in gov_keywords)

    if has_question and not has_gov_topic:
        return True

    return False

def get_enhanced_rule_response(user_message: str, user_id: str = "default") -> str:
    """Enhanced rule-based responses with context awareness - conversational like a phone assistant"""
    user_msg = user_message.lower()

    # Check if query is out of scope first
    if is_out_of_scope(user_message):
        return "I'm sorry, but I'm specifically designed to help with government services through GovConnect. I can assist with healthcare appointments, agriculture services, urban complaints, and system administration. For other topics, you might want to check with specialized services or search engines. Is there anything government-related I can help you with instead?"

    # Healthcare queries
    if any(word in user_msg for word in ["healthcare", "doctor", "appointment", "medical", "hospital", "health"]):
        if "appointment" in user_msg:
            return "Hey there! Booking a doctor appointment is super easy. Just head over to the Healthcare section and click 'Book Appointment'. Pick your hospital, choose a doctor, and select a time that works for you. You'll get a confirmation right away. Need help with anything else?"
        elif "hospital" in user_msg:
            return "Looking for hospitals? You can find all the registered ones in the Healthcare section. If you're an admin, you can even add new hospitals. Try using the search to find ones near you or by specialty. What kind of hospital are you looking for?"
        else:
            return "I'd be happy to help with healthcare stuff! Check out the Healthcare page for booking appointments, getting health info, or registering hospitals. I'm here if you need me to walk you through it!"

    # Agriculture queries
    elif any(word in user_msg for word in ["agriculture", "farm", "farmer", "crop", "irrigation", "weather"]):
        if "register" in user_msg or "farmer" in user_msg:
            return "Great! Want to register as a farmer? Go to the Agriculture section and fill out the registration form with your details, farm location, and what crops you grow. It's quick and easy! Let me know if you need help with the form."
        elif "weather" in user_msg or "forecast" in user_msg:
            return "Weather info is super important for farming! Check out the Agriculture section for current conditions, forecasts, and even pest alerts. It'll help you plan your day better. What crops are you growing?"
        elif "crop" in user_msg:
            return "Crop monitoring tools are awesome! Once you register your farm in the Agriculture dashboard, you can get personalized yield predictions and monitoring. It's like having a farming assistant. Want me to guide you through registration?"
        else:
            return "Agriculture services are fantastic here! We've got farmer registration, weather forecasts, crop monitoring, and irrigation help. What farming question can I help you with today?"

    # Urban services queries
    elif any(word in user_msg for word in ["urban", "civic", "complaint", "roads", "water", "electricity", "infrastructure"]):
        if "complaint" in user_msg or "report" in user_msg:
            return "Got a civic issue? No problem! Use the Urban Services section to report problems with roads, water, electricity, or anything else. You can track your complaint status too. What issue are you dealing with?"
        else:
            return "Urban services are all about keeping our cities running smoothly! You can report issues and check infrastructure status. Head to the Urban Services page - I'm here if you need help navigating it."

    # Admin queries
    elif any(word in user_msg for word in ["admin", "manage", "create", "delete", "update"]):
        if "alert" in user_msg:
            return "As a super admin, you can create system alerts to keep everyone informed! Check out the Alerts section for that. It's great for important announcements. What kind of alert are you thinking of?"
        elif "hospital" in user_msg:
            return "Healthcare admins can add new hospitals easily! Just go to the Healthcare section and provide the hospital details. Location, specialties, contact info - we've got it covered. Need help with the registration process?"
        else:
            return "Admin features give you lots of power! User management, hospital registration, alerts, database stuff - it's all there. Make sure you're logged in with the right admin credentials. What admin task are you working on?"

    # System queries
    elif any(word in user_msg for word in ["status", "health", "monitor", "api"]):
        return "Want to check how everything's running? The System Health page shows real-time metrics, database status, and API health. It's like a dashboard for the whole system. Everything looking good there?"

    # General assistance
    elif any(word in user_msg for word in ["help", "how", "what", "guide"]):
        return "I'm your friendly helper! I can guide you through healthcare appointments, agriculture services, urban complaints, and using the platform. Try asking me about 'booking an appointment', 'farmer registration', or 'reporting a complaint'. What's on your mind?"

    # Greeting responses
    elif any(word in user_msg for word in ["hello", "hi", "hey", "good"]):
        return "Hey there! 👋 I'm GovConnect Assistant, your friendly guide to government services. I help with healthcare, agriculture, and urban services. What can I help you with today?"

    # Default response
    else:
        return "Hi! I'm here to help with all things GovConnect - healthcare, agriculture, and urban services. Could you tell me a bit more about what you need? For example, are you looking to book an appointment, register as a farmer, or report an issue?"


