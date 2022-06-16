import glob
import xml.etree.ElementTree as ET
from datetime import datetime

import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mongo_utils import mongo_utils

def main():
    items = []
    for file in glob.glob('./*/*.xml', recursive=True):
        print(file)
        xml = ET.parse(file)
        root = xml.getroot().find('NewsML').find('NewsItem')
        
        # Get Id and Date
        iden = root.find('Identification')
        
        date = datetime.strptime(iden.find('DateLabel').text, '%d/%m/%Y %H:%M:%S')
        id = iden.find('NewsIdentifier').find('NewsItemId').text
        
        # Get headline and content
        compo = root.find('NewsComponent')
        head = compo.find('NewsLines').find('HeadLine')
        content = compo.find('ContentItem').find('DataContent')
        
        data = {'_id': id, 'date':date, 'headline':head, 'content':content}
        items.append(data)
    
    mydb = mongo_utils.get_mongo_db()
    lusa_col = mydb['lusa']

    lusa_col.insert_many(items)


if __name__ == '__main__':
    main()
