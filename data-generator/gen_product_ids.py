import datetime
import csv
import random

NUMBER_OF_PRODUCTS = 100_001
INITIAL_PRODUCT_ID = 3_278_123

headers = ['product_id','booking_country','booking_city','property_type','are_pets_allowed','has_wifi','has_parking']

file_name = f'demo_products.csv'

with open (file_name,'w') as csvfile:
  writer = csv.writer(csvfile)
  writer.writerow(headers)
  for p in range(NUMBER_OF_PRODUCTS):
    product_id = INITIAL_PRODUCT_ID + p
    booking_country = random.choices(['SP','PT','IT'],weights=[7,2,1])[0]
    if (booking_country == 'SP'):
      booking_city = random.choices(["Barcelona","Madrid","Sevilla","Valencia","Granada","Malaga","Bilbao","Alicante","Cordoba","San Sebastian"])[0]
    elif (booking_country == 'PT'):
      booking_city = random.choices(["Lisbon","Porto","Sintra","Faro","Cascais","Braga","Coimbra","Aveiro","Funchal","Évora"])[0]
    else :
      booking_city = random.choices(["Rome","Venice","Florence","Milan","Naples","Verona","Bologna","Turin","Pisa","Palermo"])[0]        
    property_type = random.choices(["hotel","apartment","villa","hostel","resort","room"], weights=[40,30,5,10,10,5])[0]
    are_pets_allowed = random.choices([0,1], weights=[7,3])[0]
    has_wifi = random.choices([0,1], weights=[7,3])[0]
    has_parking = random.choices([0,1], weights=[7,3])[0]
    writer.writerow([product_id,booking_country,booking_city,property_type,are_pets_allowed,has_wifi,has_parking])
print(file_name)