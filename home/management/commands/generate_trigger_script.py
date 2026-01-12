"""
Django Management Command to Generate the Google Apps Script TRIGGER Code
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from home.models import Subject, Counties, Level

class Command(BaseCommand):
    help = 'Generates the Google Apps Script code that listens for form submissions'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='https://www.tscswap.com', help='Base URL of your site')
        parser.add_argument('--token', type=str, help='Webhook token (found in .env)')

    def handle(self, *args, **options):
        base_url = options['url'].rstrip('/')
        webhook_url = f"{base_url}/api/google-form-webhook/"
        token = options['token'] or getattr(settings, 'GOOGLE_FORM_WEBHOOK_TOKEN', 'YOUR_SECRET_TOKEN_HERE')

        # 1. Fetch Mappings
        # Subjects
        try:
            subjects = list(Subject.objects.values('name', 'id').order_by('name'))
        except Exception:
            subjects = []
            
        # Counties (Map name -> ID)
        counties = list(Counties.objects.values('name', 'id').order_by('name'))
        
        # Build JS Objects string
        subjects_map_str = "{\n" + ",\n".join([f"    '{s['name']}': {s['id']}" for s in subjects]) + "\n  }"
        counties_map_str = "{\n" + ",\n".join([f"    '{c['name']}': {c['id']}" for c in counties]) + "\n  }"

        # 2. Build the Script
        js_code = f"""// ==========================================
// PASTE THIS CODE INTO GOOGLE APPS SCRIPT
// REPLACING EVERYTHING CURRENTLY THERE
// ==========================================

// 1. CONFIGURATION
const WEBHOOK_URL = '{webhook_url}';
const WEBHOOK_TOKEN = '{token}'; 

// 2. FORM CONFIGURATION (Must match Form Setup)
const FIELD_TITLES = {{
  FULL_NAME: 'Full Name(s)',
  PHONE: 'Phone Number', 
  EMAIL: 'Email Address',
  TEACHER_LEVEL: 'Your Teaching Level',
  SUBJECTS: 'Teaching Subjects (Select up to 2)',
  MOST_PREFERRED_COUNTY: 'Most Preferred County',
  PREFERRED_COUNTIES: 'Preferred Counties for Transfer'
}};

// 3. MAIN TRIGGER FUNCTION
function onFormSubmit(e) {{
  var itemResponses = e.response.getItemResponses();
  var payload = {{ token: WEBHOOK_TOKEN }};

  for (var i = 0; i < itemResponses.length; i++) {{
    var title = itemResponses[i].getItem().getTitle();
    var response = itemResponses[i].getResponse();

    if (title === FIELD_TITLES.FULL_NAME) payload.full_name = response;
    else if (title === FIELD_TITLES.PHONE) payload.phone = response;
    else if (title === FIELD_TITLES.EMAIL) payload.email = response;
    else if (title === FIELD_TITLES.TEACHER_LEVEL) payload.teacher_level = response;
    else if (title === FIELD_TITLES.SUBJECTS) payload.subjects = getSubjectIds(response); 
    else if (title === FIELD_TITLES.PREFERRED_COUNTIES) payload.preferred_counties = getCountyIds(response);
    else if (title === FIELD_TITLES.MOST_PREFERRED_COUNTY) payload.most_preferred_county = getCountyId(response);
  }}

  var options = {{
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  }};

  try {{
    var resp = UrlFetchApp.fetch(WEBHOOK_URL, options);
    Logger.log("Webhook Response: " + resp.getContentText());
  }} catch (err) {{
    Logger.log("Error sending webhook: " + err);
  }}
}}

// 4. ID MAPPING FUNCTIONS (Generated from Database)

function getSubjectIds(names) {{
  var map = {subjects_map_str};
  
  if (!names) return [];
  if (!Array.isArray(names)) return [map[names]];
  return names.map(function(n) {{ return map[n]; }}).filter(function(id) {{ return id != null; }});
}}

function getCountyIds(names) {{
  var map = {counties_map_str};
  
  if (!names) return [];
  if (!Array.isArray(names)) return [map[names]];
  return names.map(function(n) {{ return map[n] || n; }}).filter(function(id) {{ return id != null; }});
}}

function getCountyId(name) {{
  var map = {counties_map_str};
  return map[name] || name;
}}
"""
        with open('trigger_script.js', 'w') as f:
            f.write(js_code)
        
        self.stdout.write(self.style.SUCCESS('Successfully wrote script to trigger_script.js'))
