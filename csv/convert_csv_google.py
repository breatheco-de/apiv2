import csv
import datetime
from datetime import datetime

with open('csv/sample.csv', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)

    with open('csv/converted.csv', 'w') as new_file:
        
        csv_writer = csv.writer(new_file, delimiter=',')
        csv_writer.writerow(["Google Click ID", "Conversion Name", "Conversion Time"])
        data = []
        for line in csv_reader:
            if line[22][(len(line[22]) - 3):] == 'BwE':
                gclid = line[22]
                tags = line[23]
                created_at = datetime.strptime(line[39], '%Y-%m-%d %H:%M:%S.%f%z')
                created_at = created_at.strftime('%Y-%m-%d %H:%M:%S%z')
                data = [gclid, tags, created_at]

                csv_writer.writerow(data)



