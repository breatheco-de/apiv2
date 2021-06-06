import csv
import datetime

def read_csv(path):
    file = open(path, newline='')
    reader = csv.DictReader(file)
    return reader

def write_googlead_csv(reader):
    new_file = open('../google_ads.csv', 'w')
    field_names = ['gclid', 'tags', 'created_at']

    csv_writer = csv.DictWriter(new_file, field_names, delimiter=',')
    csv_writer.writeheader()

    for line in reader:
        line['Google Click ID'] = line['gclid']
        del line['gclid']

        line['Conversion Name'] = line['tags']
        del line['tags']
        
        time = datetime.datetime.fromisoformat(line['created_at'])



