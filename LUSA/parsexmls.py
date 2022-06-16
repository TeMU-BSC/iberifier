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
        root = xml.getroot()['NewsML']['NewsItem']
        
        # Get Id and Date
        iden = root['Identification']
        if 'DateLabel' in iden: 
            date = datetime.strptime(iden['DateLabel'].text, '%d/%m/%Y %H:%M:%S')
        if 'NewsIdentifier' in iden and 'NewsItemId' in iden['NewsIdentifier']:
            id = iden['NewsIdentifier']['NewsItemId'].text
        
        # Get headline and content
        compo = root['NewsComponent']
        if 'NewsLines' in compo and 'HeadLine' in compo['NewsLines']:
            head = compo['NewsLines']['HeadLine']
        if 'ContentItem' in compo and 'DataContent' in compo['ContentItem']:
            content = compo['ContentItem']['DataContent']
        
        data = {'_id': id, 'date':date, 'headline':head, 'content':content}
        items.append(data)
    
    mydb = mongo_utils.get_mongo_db()
    lusa_col = mydb['lusa']

    lusa_col.insert_many(items)


if __name__ == '__main__':
    main()
