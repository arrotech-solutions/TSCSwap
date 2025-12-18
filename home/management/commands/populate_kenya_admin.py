from django.core.management.base import BaseCommand
from home.models import Counties, Constituencies, Wards

class Command(BaseCommand):
    help = 'Populates the database with Kenya administrative data (Counties, Constituencies, Wards)'

    def handle(self, *args, **options):
        # Kenya administrative data

        KENYA_ADMIN={}

        KENYA_ADMIN = {

    "Baringo": {
        "Baringo North": [
            "Barwessa",
            "Kabartonjo",
            "Saimo/Kipsaraman",
            "Saimo/Soi",
            "Bartabwa",
        ],
        "Baringo Central": [
            "Kabarnet",
            "Sacho",
            "Tenges",
            "Ewalel/Chapchap",
            "Kapropita",
        ],
        "Baringo South": [
            "Mochongoi",
            "Mukutani",
            "Marigat",
            "Ilchamus",
        ],
        "Eldama Ravine": [
            "Lembus",
            "Lembus Kwen",
            "Ravine",
            "Mumberes/Maji Mazuri",
            "Lembus/Perkerra",
        ],
        "Tiaty": [
            "Tirioko",
            "Kolowa",
            "Ribkwo",
            "Silale",
            "Loiyamorock",
            "Tangulbei/Korossi",
            "Churo/Amaya",
        ],
    },

    "Bomet": {
        "Bomet Central": [
            "Silibwet Township",
            "Ndaraweta",
            "Singorwet",
            "Chesoen",
            "Mutarakwa",
        ],
        "Bomet East": [
            "Merigi",
            "Kembu",
            "Longisa",
            "Kipreres",
            "Chemaner",
        ],
        "Chepalungu": [
            "Chepalungu",
            "Sigor",
            "Chebunyo",
            "Siongiroi",
        ],
        "Sotik": [
            "Ndanai/Abosi",
            "Chemagel",
            "Kapletundo",
            "Rongena/Manaret",
        ],
        "Konoin": [
            "Kimulot",
            "Mogogosiek",
            "Boito",
            "Embomos",
        ],
    },

    "Bungoma": {
        "Bumula": [
            "Bumula",
            "Kabula",
            "Kimaeti",
            "South Bukusu",
            "Siboti",
        ],
        "Kabuchai": [
            "Kabuchai/Chwele",
            "West Nalondo",
            "Bwake/Luuya",
            "Mukuyuni",
        ],
        "Kanduyi": [
            "Bukembe West",
            "Bukembe East",
            "Township",
            "Khalaba",
            "Musikoma",
            "East Sang'alo",
            "West Sang'alo",
        ],
        "Kimilili": [
            "Kimilili",
            "Maeni",
            "Kamukuywa",
        ],
        "Mt. Elgon": [
            "Cheptais",
            "Chesikaki",
            "Chepyuk",
            "Kapkateny",
            "Kaptama",
            "Elgon",
        ],
        "Sirisia": [
            "Namwela",
            "Malakisi/South Kulisiru",
            "Lwandanyi",
        ],
        "Tongaren": [
            "Mihuu",
            "Naitiri/Kabuyefwe",
            "Milima",
            "Ndalu/Tabani",
            "Tongaren",
            "Soysambu/Mitua",
        ],
        "Webuye East": [
            "Webuye East",
            "Mihuu",
        ],
        "Webuye West": [
            "Webuye West",
            "Misikhu",
            "Matulo",
        ],
    },

    "Busia": {
        "Budalangi": [
            "Bunyala Central",
            "Bunyala North",
            "Bunyala South",
            "Bunyala West",
        ],
        "Butula": [
            "Marachi West",
            "Marachi Central",
            "Marachi East",
            "Marachi North",
            "Elugulu",
        ],
        "Funyula": [
            "Namboboto/Nambuku",
            "Ageng'a Nanguba",
            "Bwiri",
        ],
        "Matayos": [
            "Bukhayo West",
            "Bukhayo East",
            "Bukhayo Central",
        ],
        "Nambale": [
            "Nambale Township",
            "Bukhayo North/Walatsi",
            "Bukhayo South/Buyofu",
        ],
        "Teso North": [
            "Malaba Central",
            "Malaba North",
            "Ang'urai South",
            "Ang'urai North",
            "Ang'urai East",
        ],
        "Teso South": [
            "Amukura West",
            "Amukura East",
            "Amukura Central",
        ],
    },

    "Elgeyo-Marakwet": {
        "Keiyo North": [
            "Emsoo",
            "Kamariny",
            "Kapchemutwa",
            "Tambach",
        ],
        "Keiyo South": [
            "Kaptarakwa",
            "Chepkorio",
            "Soy North",
            "Soy South",
            "Kabiemit",
            "Metkei",
        ],
        "Marakwet East": [
            "Kapyego",
            "Sambirir",
            "Endo",
            "Embobut/Embulot",
        ],
        "Marakwet West": [
            "Lelan",
            "Sengwer",
            "Cherang'any/Chebororwa",
            "Moiben/Kuserwo",
        ],
    },

}


        # Clear existing data
        # self.stdout.write('Clearing existing data...')
        # Wards.objects.all().delete()
        # Constituencies.objects.all().delete()
        # Counties.objects.all().delete()

        # Populate the database
        for county_name, constituencies in KENYA_ADMIN.items():
            # Create or get county
            county, created = Counties.objects.get_or_create(name=county_name)
            self.stdout.write(self.style.SUCCESS(f'Processing county: {county_name}'))
            
            for constituency_name, wards in constituencies.items():
                # Create or get constituency
                constituency, created = Constituencies.objects.get_or_create(
                    name=constituency_name,
                    county=county
                )
                self.stdout.write(f'  - Processing constituency: {constituency_name}')
                
                for ward_name in wards:
                    # Create or get ward
                    ward, created = Wards.objects.get_or_create(
                        name=ward_name,
                        constituency=constituency
                    )
                    self.stdout.write(f'    - Added ward: {ward_name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated Kenya administrative data!'))
