import glob
import xml.etree.ElementTree as ET
from datetime import datetime

import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils

def main():
    items = []
    for file in glob.glob('mynews/*.xml', recursive=True):
        print(file)
        xml = ET.parse(file)
        root = xml.getroot().findall('articulo')
        print(root)

        for articulo in root:

            # Get metadata
            head = articulo.find('head')

            id = head.find('IdDocument').text
            date = datetime.strptime(head.find('DREDATE').text, '%Y/%m/%d')
            newspaper = head.find('Newspaper').text
            title = head.find('Title').text
            subtitle = head.find('Subtitle').text
            author = head.find('Author').text
            url = head.find('Page').text

            # Get content
            content = articulo.find('body').find('DRECONTENT').text

            data = {'_id': id, 'date':date, 'headline':title, 'content':content, 'newspaper': newspaper, 'subtitle': subtitle, 'author':author, 'url': url}
            items.append(data)

    mydb = mongo_utils.get_mongo_db()
    mynews_col = mydb['mynews']

    mynews_col.insert_many(items)


if __name__ == '__main__':
    main()
