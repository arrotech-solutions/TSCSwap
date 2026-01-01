import json
import os
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from dotenv import load_dotenv
from openai import OpenAI

from .models import AIResponse, UserQuery
from .intent_detection import IntentType, get_intent_detector
from .whatsapp_integration import (
    generate_response as whatsapp_generate_response,
    format_profile_data,
    answer_swap_question,
    get_profile_completeness_links,
    is_greeting,
    get_welcome_message,
    whatsapp_client,
    normalize_phone_number
)

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(env_path)

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to your .env file.")

client = OpenAI(api_key=openai_api_key)

def convert_whatsapp_to_web_format(text: str) -> str:
    """
    Convert WhatsApp-style formatting to web-friendly HTML.
    - *bold* -> <strong>bold</strong>
    - Emojis are kept as-is
    - URLs are converted to clickable links
    - Line breaks are preserved
    """
    import re
    
    if not text:
        return ""
    
    # Convert *bold* to <strong>bold</strong>
    text = re.sub(r'\*([^*]+)\*', r'<strong>\1</strong>', text)
    
    # Convert URLs to clickable links
    url_pattern = r'(https?://[^\s]+)'
    text = re.sub(url_pattern, r'<a href="\1" target="_blank" style="color: #14b8a6; text-decoration: underline;">\1</a>', text)
    
    # Convert line breaks to <br> tags
    text = text.replace('\n', '<br>')
    
    return text

def generate_web_response(user_message: str, intent: IntentType, entities: dict, user, conversation_history: list = None) -> str:
    """
    Generate a web-friendly response using the smart bot logic.
    This adapts the WhatsApp generate_response for web use.
    """
    # Handle greetings
    if is_greeting(user_message):
        return convert_whatsapp_to_web_format(get_welcome_message())
    
    # Handle different intents
    if intent == IntentType.GET_PROFILE:
        if user and user.is_authenticated:
            # Format profile data for web
            profile_text = format_profile_data(user, None)  # No phone number needed for web
            return convert_whatsapp_to_web_format(profile_text)
        else:
            return "Please <a href='/users/login/'>login</a> to view your profile."
    
    elif intent == IntentType.FIND_SWAPS:
        if not user or not user.is_authenticated:
            return "Please <a href='/users/login/'>login</a> to find swap opportunities."
        
        # Get location from entities
        location = entities.get('location', '').strip() if entities.get('location') else None
        
        # Get user's teaching level
        try:
            user_profile = user.profile
            user_level = user_profile.level if user_profile and user_profile.level else None
            
            if not user_level:
                completeness_msg = get_profile_completeness_links(user)
                msg = f"""Your profile doesn't have a teaching level set. Please set your teaching level to find matching swaps."""
                if completeness_msg:
                    msg += convert_whatsapp_to_web_format(completeness_msg)
                return msg
        except Exception as e:
            print(f"Error getting user profile: {str(e)}")
            return "Error loading your profile. Please try again later."
        
        # Use WhatsApp generate_response logic but adapt for web
        # We'll call the WhatsApp function but convert the response
        try:
            from .whatsapp_integration import find_swaps_by_location, format_swap_results, find_triangle_swaps_for_whatsapp
            
            # Check if location is provided, if not, use swap preferences
            using_preferences = False
            preference_counties = []
            preference_county_names = []
            
            if not location:
                try:
                    if hasattr(user, 'swappreference') and user.swappreference:
                        swap_pref = user.swappreference
                        if swap_pref.desired_county:
                            preference_counties.append(swap_pref.desired_county)
                            preference_county_names.append(swap_pref.desired_county.name)
                        open_to_all_counties = swap_pref.open_to_all.all()
                        for county in open_to_all_counties:
                            if county not in preference_counties:
                                preference_counties.append(county)
                                preference_county_names.append(county.name)
                        if preference_counties:
                            using_preferences = True
                except Exception as e:
                    print(f"Error getting swap preferences: {str(e)}")
            
            # Find matching swaps
            if using_preferences:
                matching_users, error_info = find_swaps_by_location(None, user_level, user, counties_list=preference_counties)
                search_location = ", ".join(preference_county_names[:3])
                if len(preference_county_names) > 3:
                    search_location += f" +{len(preference_county_names) - 3} more"
            else:
                matching_users, error_info = find_swaps_by_location(location, user_level, user)
                search_location = location
            
            # Find triangle swaps
            triangle_swaps_text = ""
            if location or using_preferences:
                triangle_location = location if location else (preference_county_names[0] if preference_county_names else None)
                if triangle_location:
                    triangle_swaps_text = find_triangle_swaps_for_whatsapp(user, triangle_location, user_level)
            
            # Build response
            if matching_users:
                response = format_swap_results(matching_users, search_location, user_level, using_preferences=using_preferences)
                if triangle_swaps_text:
                    response += f"\n\n━━━━━━━━━━━━━━━━━━━━\n\n{triangle_swaps_text}"
                return convert_whatsapp_to_web_format(response)
            else:
                # No swaps found
                if error_info.get('no_counties_found') and location:
                    suggestions = error_info.get('suggestions', [])
                    if suggestions:
                        suggestions_text = "<br>".join([f"   • {s}" for s in suggestions])
                        response = f"""Location not found: "{location}"<br><br>Did you mean one of these?<br>{suggestions_text}<br><br>Try searching again with the correct county name! 😊"""
                    else:
                        response = f"""Location not found: "{location}"<br><br>Please check the spelling and try again. Make sure you're using a valid Kenyan county name."""
                    return convert_whatsapp_to_web_format(response)
                elif using_preferences:
                    response = f"""No direct matching swaps found in your preferred counties: {search_location}<br><br>Try:<br>• Searching with a specific location (e.g., "Find swaps in Nairobi")<br>• Updating your swap preferences<br>• Checking if your teaching level is correctly set"""
                    completeness_msg = get_profile_completeness_links(user)
                    if completeness_msg:
                        response += convert_whatsapp_to_web_format(completeness_msg)
                    if triangle_swaps_text:
                        response += f"<br><br>{convert_whatsapp_to_web_format(triangle_swaps_text)}"
                    return response
                elif location:
                    is_secondary = user_level and ('secondary' in user_level.name.lower() or 'high' in user_level.name.lower())
                    if is_secondary:
                        response = f"""No matching swaps found in {location} right now.<br><br>For secondary/high school teachers, I look for matches with:<br>• Same teaching level<br>• Common subjects<br><br>I couldn't find any teachers in {location} who meet both criteria."""
                    else:
                        response = f"""No matching swaps found in {location} right now.<br><br>I couldn't find any teachers in {location} who teach at the same level as you."""
                    completeness_msg = get_profile_completeness_links(user)
                    if completeness_msg:
                        response += convert_whatsapp_to_web_format(completeness_msg)
                    if triangle_swaps_text:
                        response += f"<br><br>{convert_whatsapp_to_web_format(triangle_swaps_text)}"
                    return response
                else:
                    completeness_msg = get_profile_completeness_links(user)
                    response = f"""You didn't specify a location, and I couldn't find your swap preferences.<br><br>To find swaps:<br>1. Specify a location (e.g., "Find swaps in Nairobi")<br>2. Set your swap preferences: <a href="https://www.tscswap.com/preferences/">https://www.tscswap.com/preferences/</a>"""
                    if completeness_msg:
                        response += convert_whatsapp_to_web_format(completeness_msg)
                    return response
        except Exception as e:
            import traceback
            print(f"Error finding swaps: {str(e)}\n{traceback.format_exc()}")
            return "Error searching for swaps. Please try again later."
    
    elif intent == IntentType.ASK_QUESTION:
        # Use answer_swap_question for general questions
        response = answer_swap_question(user_message, user=user, conversation_history=conversation_history)
        return convert_whatsapp_to_web_format(response)
    
    elif intent == IntentType.REQUEST_CALL:
        # Get user's phone number for notification
        requester_phone = "Unknown"
        if user and user.is_authenticated:
            try:
                profile = user.profile
                if profile and profile.phone:
                    requester_phone = profile.phone
            except Exception as e:
                print(f"Error getting user phone: {str(e)}")
        
        # Send notification to admin via WhatsApp
        admin_phone = "254742134431"
        notification_message = f"Callback request from {requester_phone}"
        
        try:
            result = whatsapp_client.send_text_message(admin_phone, notification_message)
            if result:
                print(f"✅ Callback notification sent to admin: {admin_phone}")
            else:
                print(f"❌ Failed to send callback notification to admin")
        except Exception as e:
            print(f"Error sending callback notification: {str(e)}")
        
        return "I've noted your request for a callback. Our support team will contact you shortly!<br><br>In the meantime, feel free to ask me any questions about TSC Swap. 😊"
    
    elif intent == IntentType.UPDATE_PREFERENCE:
        return "To update your preferences, please visit your <a href='/users/profile/edit/'>profile edit page</a> or <a href='/preferences/'>swap preferences page</a>."
    
    else:
        # Unknown intent - use answer_swap_question as fallback
        response = answer_swap_question(user_message, user=user, conversation_history=conversation_history)
        return convert_whatsapp_to_web_format(response)

@require_http_methods(["GET", "POST"])
@csrf_exempt
def chat_view(request):
    """
    Chat view that works for both authenticated and anonymous users.
    - Authenticated users: Chat history is saved and retrieved
    - Anonymous users: Chat works but history is not saved (session-based only)
    """
    if request.method == 'GET':
        # Return chat history for authenticated users only
        try:
            if not request.user.is_authenticated:
                return JsonResponse({'chats': []})  # No history for anonymous users
                
            chats = UserQuery.objects.filter(user=request.user).order_by('-created_at')[:10]
            chat_history = []
            
            for chat in chats:
                try:
                    ai_response = chat.ai_response
                    chat_history.append({
                        'user_message': chat.message,
                        'ai_message': ai_response.message,
                        'timestamp': chat.created_at.isoformat()
                    })
                except AIResponse.DoesNotExist:
                    continue
                    
            return JsonResponse({'chats': chat_history})
            
        except Exception as e:
            print(f"Chat GET error: {str(e)}")
            return JsonResponse({'chats': []})  # Return empty on error instead of 500
    
    elif request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '').strip()
            
            if not user_message:
                return JsonResponse({'error': 'Message cannot be empty'}, status=400)
            
            # Use smart bot with intent detection
            if request.user.is_authenticated:
                # Authenticated user - use smart bot features
                with transaction.atomic():
                    # Save user query
                    user_query = UserQuery.objects.create(
                        user=request.user,
                        message=user_message
                    )
                    
                    try:
                        # Get conversation history for context
                        conversation_history = []
                        previous_chats = UserQuery.objects.filter(user=request.user).exclude(pk=user_query.pk).order_by('-created_at')[:5]
                        
                        # Format previous messages in reverse chronological order (oldest first)
                        for chat in reversed(previous_chats):
                            try:
                                ai_response = chat.ai_response
                                conversation_history.append({"role": "user", "content": chat.message})
                                conversation_history.append({"role": "assistant", "content": ai_response.message})
                            except AIResponse.DoesNotExist:
                                continue
                        
                        # Detect intent using the smart bot
                        intent_detector = get_intent_detector()
                        intent, entities = intent_detector.detect_intent(user_message)
                        
                        # Generate response using smart bot (adapted for web)
                        # Note: We pass None for phone_number since we're using request.user
                        ai_message = generate_web_response(
                            user_message=user_message,
                            intent=intent,
                            entities=entities,
                            user=request.user,
                            conversation_history=conversation_history
                        )
                        
                        # Convert WhatsApp-style formatting to web-friendly HTML
                        ai_message = convert_whatsapp_to_web_format(ai_message)
                        
                        # Save AI response
                        AIResponse.objects.create(
                            query=user_query,
                            message=ai_message
                        )
                        
                        return JsonResponse({
                            'success': True,
                            'user_message': user_message,
                            'ai_message': ai_message,
                            'timestamp': timezone.now().isoformat()
                        })
                        
                    except Exception as e:
                        import traceback
                        print(f"Error generating AI response: {str(e)}\n{traceback.format_exc()}")
                        return JsonResponse({
                            'success': False,
                            'error': 'Sorry, there was an error processing your request. Please try again later.'
                        }, status=500)
            
            else:
                # Anonymous user - provide basic AI response with login prompt
                try:
                    # Detect intent even for anonymous users
                    intent_detector = get_intent_detector()
                    intent, entities = intent_detector.detect_intent(user_message)
                    
                    # Handle greetings
                    if is_greeting(user_message):
                        welcome_msg = get_welcome_message()
                        ai_message = convert_whatsapp_to_web_format(welcome_msg)
                        ai_message += "\n\n⚠️ <strong>Note:</strong> To use advanced features like finding swaps or viewing your profile, please <a href='/users/login/'>login</a> or <a href='/users/signup/'>create an account</a>."
                    elif intent == IntentType.FIND_SWAPS or intent == IntentType.GET_PROFILE:
                        # Require login for these actions
                        ai_message = f"""To {intent.value.replace('_', ' ').title()}, you'll need to create an account or login first!

👉 <a href="/users/login/" style="color: #14b8a6; text-decoration: underline;">Login here</a> if you already have an account
👉 <a href="/users/signup/" style="color: #14b8a6; text-decoration: underline;">Register here</a> to create a new account

Once logged in, you'll be able to browse swaps, create your own swap requests, and get personalized matches based on your preferences!"""
                    else:
                        # Use answer_swap_question for general questions
                        ai_message = answer_swap_question(user_message, user=None, conversation_history=None)
                        ai_message = convert_whatsapp_to_web_format(ai_message)
                        ai_message += "\n\n💡 <strong>Tip:</strong> <a href='/users/signup/'>Create an account</a> to access all features like finding swaps and viewing your profile!"
                    
                    return JsonResponse({
                        'success': True,
                        'user_message': user_message,
                        'ai_message': ai_message,
                        'timestamp': timezone.now().isoformat()
                    })
                    
                except Exception as e:
                    import traceback
                    print(f"Error generating AI response for anonymous user: {str(e)}\n{traceback.format_exc()}")
                    return JsonResponse({
                        'success': False,
                        'error': 'Sorry, there was an error processing your request. Please try again later.'
                    }, status=500)
                    
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
