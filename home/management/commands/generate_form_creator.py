"""
Django Management Command to Generate a Google Apps Script that CREATES the Form
"""
from django.core.management.base import BaseCommand
from home.models import Subject, Counties, Level

class Command(BaseCommand):
    help = 'Generates a Google Apps Script to create the TSCSwap Form automatically'

    def handle(self, *args, **options):
        # 1. Fetch Data
        try:
            # Find Secondary level
            sec_level = Level.objects.filter(name__icontains="Secondary").first()
            if sec_level:
                subjects = list(Subject.objects.filter(level=sec_level).values_list('name', flat=True).order_by('name'))
            else:
                subjects = []
            
            if not subjects:
                 # Fallback if DB is empty for secondary subjects
                 subjects = ['Mathematics', 'English', 'Kiswahili', 'Biology', 'Chemistry', 'Physics', 'History', 'Geography', 'CRE', 'IRE', 'HRE', 'Business Studies', 'Agriculture', 'Home Science', 'Computer Studies', 'French', 'German', 'Arabic', 'Music', 'Art & Design']
        except Exception:
            subjects = []
            
        counties = list(Counties.objects.values_list('name', flat=True).order_by('name'))
        if not counties:
             # Fallback
             counties = ["Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo Marakwet", "Embu", "Garissa", "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi", "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos", "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a", "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu", "Siaya", "Taita Taveta", "Tana River", "Tharaka Nithi", "Trans Nzoia", "Turkana", "Uasin Gishu", "Vihiga", "Wajir", "West Pokot"]

        # Format lists for JS
        subjects_js = str(subjects)
        counties_js = str(counties)

        # 2. Start building the JS code
        js_code = f"""
function createTSCSwapForm() {{
  // 1. UPDATED TITLE and DESCRIPTION
  var form = FormApp.create('Find A Swap Mate');
  form.setDescription('This form is for all the teachers looking to find a suitable swap mate.');
  
  // === PAGE 1: PERSONAL INFO ===
  form.addTextItem().setTitle('Full Name(s)').setRequired(true);

  // 2. UPDATED PHONE INSTRUCTIONS
  var phoneVal = FormApp.createTextValidation()
      .setHelpText('Enter valid phone starting with 0')
      .requireTextMatchesPattern('^0[0-9]{{9}}$')
      .build();
      
  form.addTextItem()
      .setTitle('Phone Number')
      .setHelpText('WhatsApp phone number is most preferred for communication purposes')
      .setRequired(true)
      .setValidation(phoneVal);

  var emailVal = FormApp.createTextValidation().requireTextIsEmail().build();
  form.addTextItem().setTitle('Email Address').setRequired(true).setValidation(emailVal);

  // TEACHING LEVEL with (JSS included)
  var teachingLevel = form.addMultipleChoiceItem()
      .setTitle('Your Teaching Level')
      .setRequired(true);

  // === PAGE 2: TEACHING SUBJECTS ===
  var subjectPage = form.addPageBreakItem().setTitle('Teaching Subjects');
  
  form.addCheckboxItem()
      .setTitle('Teaching Subjects (Select up to 2)')
      .setChoiceValues({subjects_js})
      .setValidation(FormApp.createCheckboxValidation().requireSelectAtMost(2).build());

  // === PAGE 3: LOCATION PREFERENCES ===
  var mainPage = form.addPageBreakItem().setTitle('Location Preferences');

  // REORDERED: Most Preferred County FIRST
  form.addListItem()
      .setTitle('Most Preferred County')
      .setChoiceValues({counties_js})
      .setRequired(true);

  // Then Preferred (Acceptable) Counties SECOND
  form.addCheckboxItem()
      .setTitle('Preferred Counties for Transfer')
      .setChoiceValues({counties_js})
      .setRequired(true)
      .setValidation(FormApp.createCheckboxValidation().requireSelectAtLeast(1).build());

  // === CONNECTING THE LOGIC ===
  teachingLevel.setChoices([
      teachingLevel.createChoice('Primary', mainPage),
      teachingLevel.createChoice('Secondary/High School (JSS included)', subjectPage)
  ]);

  subjectPage.setGoToPage(mainPage); 

  Logger.log('Form Created! URL: ' + form.getEditUrl());
}}
"""
        with open('form_creator.js', 'w') as f:
            f.write(js_code)
        
        self.stdout.write(self.style.SUCCESS('Successfully wrote script to form_creator.js'))
