import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from openai import OpenAI

class IntentType(Enum):
    GET_PROFILE = "get_profile_info"
    FIND_SWAPS = "find_swaps"
    REQUEST_CALL = "request_call"
    UPDATE_PREFERENCE = "update_swap_preference"
    UNKNOWN = "unknown"

class IntentDetector:
    """
    Detects user intent from messages using OpenAI's language understanding capabilities.
    """
    
    def __init__(self):
        # Load environment variables
        env_path = Path(__file__).resolve().parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        # Initialize OpenAI client
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")
        
        self.client = OpenAI(api_key=openai_api_key)
        
        # Intent descriptions for the system prompt
        self.intent_descriptions = {
            IntentType.GET_PROFILE: "User wants to view, see, or get information about their profile, account details, or personal information. Examples: 'show my profile', 'who am i', 'my account info'",
            IntentType.FIND_SWAPS: "User wants to find, search for, or discover swap opportunities, exchanges, trades, matches, or partners. Examples: 'find swaps', 'show me available exchanges', 'who can i swap with'",
            IntentType.REQUEST_CALL: "User wants to be called, contacted, or speak to someone (support, admin, help). Examples: 'call me', 'can someone contact me', 'request a callback'",
            IntentType.UPDATE_PREFERENCE: "User wants to update, change, modify, or edit their preferences, settings, location, subject, school, grade, or class. Examples: 'update my preferences', 'change my location', 'modify my subject'",
            IntentType.UNKNOWN: "The message doesn't clearly match any of the above intents or is unclear, ambiguous, or unrelated to the TSC Swap platform."
        }
    
    def detect_intent(self, message: str) -> Tuple[IntentType, Dict]:
        """
        Detect the intent from a given message using OpenAI.
        
        Args:
            message: The user's message text
            
        Returns:
            A tuple of (intent_type, entities)
            - intent_type: The detected intent (IntentType enum)
            - entities: A dictionary of extracted entities (e.g., location, subject)
        """
        if not message or not isinstance(message, str):
            return IntentType.UNKNOWN, {}
        
        message = message.strip()
        if not message:
            return IntentType.UNKNOWN, {}
        
        try:
            # Create system prompt for intent detection
            system_prompt = """You are an intent detection system for TSC Swap, a platform that helps teachers find suitable swap mates.

Your task is to analyze user messages and determine their intent. The possible intents are:

1. get_profile_info: User wants to view, see, or get information about their profile, account details, or personal information.
   Examples: "show my profile", "who am i", "my account info", "view my details"

2. find_swaps: User wants to find, search for, or discover swap opportunities, exchanges, trades, matches, or partners.
   Examples: "find swaps", "show me available exchanges", "who can i swap with", "search for matches", "look for swap partners"

3. request_call: User wants to be called, contacted, or speak to someone (support, admin, help).
   Examples: "call me", "can someone contact me", "request a callback", "I need to speak to support"

4. update_swap_preference: User wants to update, change, modify, or edit their preferences, settings, location, subject, school, grade, or class.
   Examples: "update my preferences", "change my location to Nairobi", "modify my subject", "edit my school preference"

5. unknown: The message doesn't clearly match any of the above intents or is unclear, ambiguous, or unrelated to TSC Swap.

Additionally, extract relevant entities from the message:
- location: Any location mentioned (county, city, area, school name, etc.)
- subject: Any subject or teaching subject mentioned

Respond with a JSON object in this exact format:
{
    "intent": "intent_name",
    "entities": {
        "location": "extracted location or null",
        "subject": "extracted subject or null"
    }
}

Only include entities if they are clearly mentioned in the message. Use null if not present."""

            # Call OpenAI to detect intent
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this message and detect the intent: {message}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent classification
                max_tokens=200,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Parse the response
            response_content = response.choices[0].message.content.strip()
            result = json.loads(response_content)
            
            # Extract intent
            intent_str = result.get("intent", "unknown").lower()
            intent_type = IntentType.UNKNOWN
            
            # Map string to IntentType enum
            intent_mapping = {
                "get_profile_info": IntentType.GET_PROFILE,
                "find_swaps": IntentType.FIND_SWAPS,
                "request_call": IntentType.REQUEST_CALL,
                "update_swap_preference": IntentType.UPDATE_PREFERENCE,
                "unknown": IntentType.UNKNOWN
            }
            
            intent_type = intent_mapping.get(intent_str, IntentType.UNKNOWN)
            
            # Extract entities
            entities = result.get("entities", {})
            # Clean up entities - remove null values
            entities = {k: v for k, v in entities.items() if v and v != "null" and v.lower() != "null"}
            
            return intent_type, entities
            
        except json.JSONDecodeError as e:
            print(f"Error parsing OpenAI response as JSON: {e}")
            print(f"Response content: {response_content if 'response_content' in locals() else 'N/A'}")
            return IntentType.UNKNOWN, {}
        except Exception as e:
            print(f"Error detecting intent with OpenAI: {e}")
            return IntentType.UNKNOWN, {}

def get_intent_detector() -> IntentDetector:
    """Factory function to get an intent detector instance."""
    return IntentDetector()
