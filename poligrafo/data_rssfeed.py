import feedparser


def parse_entry(entry):
    #TODO
    # Entry keys
    # ['title', 'title_detail', 'links', 'link', 'summary', 'summary_detail', 
    # 'published', 'published_parsed', 'id', 'guidislink', 'sapo_lead', 
    # 'sapo_body', 'sapo_embed', 'sapo_id', 'sapo_item', 'sapo_items',
    # 'sapo_embeds', 'sapo_author', 'sapo_authorphoto']
    print(entry.title)
    print(entry.published)

def main(limit_page=-1):
    page = 0
    start = 0
    total = 1

    # Go through all the rss feed pages until reaching the limit
    # or the imposed page limit
    while start<total and (limit_page <0 or page < limit_page):
        page += 1
        rss = feedparser.parse('https://poligrafo.sapo.pt/feed?type=fact-check&page={}'.format(page))
        start = int(rss.feed['sapo_start'])
        total = int(rss.feed['sapo_total'])
        entries = rss.entries
        for e in entries:
            parse_entry(e)

if __name__ == "__main__":
    main(2)