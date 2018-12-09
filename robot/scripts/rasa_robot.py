# coding: utf-8

from random import choice
from requests import get
from bs4 import BeautifulSoup
from collections import namedtuple
from warnings import filterwarnings
import sqlite3 as sql

filterwarnings('ignore')

JOKE_ADDR = 'https://www.qiushibaike.com/text/'
STOCK_ADDR = 'http://hq.sinajs.cn/list=%s%s'
STOCK_FORMAT = ['Name', 'Open', 'High', 'Low', 'Current', 'volume']
NEWS_ADDR = 'http://search.sina.com.cn/?q=%s&range=all&c=news&sort=time'
NEWS_FORMAT = namedtuple('news', ['Keyword', 'Title', 'Link'])

RESPONSE_GREET = ['Hello, dear user!', 'Nice to see you!', 'What can I do for you?']
RESPONSE_THANKYOU = ['It is my pleasure', 'No problem!', 'You are welcome!']
RESPONSE_GOODBYE = ['See you!', 'See you next time!', 'Hope to see you next time', 'Bye']
RESPONSE_HELP = ['My father is Moe, he might be sleepng now, at least you have me',
                 'I can help you search the latest data about the market, such as news and price!',
                 'I can also tell you jokes!']
RESPONSE_CHOOSE = ['Do you like it?', 'Are you interested in it?', 'What about this?', 'A better one']
RESPONSE_NOTHING = ["I can't understand what you said.", "Sorry, I did not get your point ...",
                    'Sorry, I can only get some information of market for you ...']


class Robot:
    
    def __init__(self, conn, interpreter):
        self._conn = conn
        self._interpreter = interpreter

    def session(self):
        intent = self.listen()
        if intent['intent'] == u'greet':
            self.response(choice(RESPONSE_GREET))

        elif intent['intent'] == u'thankyou':
            self.response(choice(RESPONSE_THANKYOU))
            return False

        elif intent['intent'] == u'goodbye':
            self.response(choice(RESPONSE_GOODBYE))
            return False

        elif intent['intent'] == u'search_stock':
            stock, subject = intent.get('stock', None), intent.get('subject', None)
            if stock and subject:
                self.response('I am searching for %s, please wait...' % stock)
            elif stock and not subject:
                subject = self.ask('Which information you want to know about %s, price, news or market?' % stock.upper(), False)
            elif not stock and subject:
                stock = self.ask("which company's %s do you want to know " % subject, False)
            else:
                stock = self.ask("Sorry, I didn't hear clearly, which company?", False)
                subject = self.ask('What you want to know about %s, news, price or volume?' % stock, False)
            if subject in ('news', 'new', 'info', 'information', 'Journalism'):
                self.do_news(news=None, i=0, key=stock)
            else:
                self.do_stock(stock, subject)

        elif intent['intent'] == u'search_news':
            key = intent.get('key', None)
            while not key:
                key = self.ask("OK, please tell me some keywords of the news.", False)
            self.do_news(news=None, i=0, key=key)
            
        elif intent['intent'] == u'search_market':
            self.do_market(intent.get('country', None))
            
        elif intent['intent'] == u'help':
           self.response(choice(RESPONSE_HELP))
           
        else:
            self.response(choice(RESPONSE_NOTHING))
            
        return True
            
    def listen(self, parse=True):
        MSG = self._conn.recv(1024).strip().decode('utf-8')
        print 'Say: %s' % MSG

        if not parse:
            return MSG

        parse = self._interpreter.parse(MSG)
        obj = {'intent':parse[u'intent'][u'name']}
        if obj['intent'] == u'search_stock':
            for ent in parse[u'entities']:
                if ent.get(u'entity') == 'stock':
                    obj['stock'] = ent[u'value'].encode('utf-8')
                elif ent.get(u'entity') == 'subject':
                    obj['subject'] = ent[u'value'].encode('utf-8')
                    
        elif obj['intent'] == u'search_news':
            for ent in parse[u'entities']:
                if ent.get(u'entity') == 'key':
                    obj['key'] = ent[u'value'].encode('utf-8')
                    
        elif obj['intent'] == u'search_market':
            for ent in parse[u'entities']:
                if ent.get(u'entity') == 'country':
                    obj['country'] = ent[u'value'].encode('utf-8')
        return obj

    def response(self, msg):

        if isinstance(msg, list):
            msg = '\n'.join([every.encode('utf-8') for every in msg if every])
        self._conn.sendall(msg.encode('utf-8') + '\n')

    def ask(self, msg, parse=True):

        self.response(msg)
        self.response('INPUT')
        return self.listen(parse)
    
    def do_market(self, market):
        if market is None:
            market = self.ask('Which market do you prefer, US or China?', False).upper()
            self.do_market(market)
        elif market in ('US', 'U.S', 'U.S.', 'U.S.A', 'AMERICAN', 'UNITED STATES', 'THE UNITED STATES'):
            _nas = self.get_stock('nasdaq')
            _sp = self.get_stock('biaopu')
            _djz = self.get_stock('djz')
            self.response(u'NASDAQ: %s | S&P 500: %s | Dow Jones: %s' % (_nas, _sp, _djz))
        elif market in ('CHINA', 'CHINESE', 'CHIAN'):
            _shanghai = self.get_stock('shanghai')
            _shenzheng = self.get_stock('shenzheng')
            self.response('Shanghai Composite Index: %s  |  Shenzhen Stock Index: %s' % (_shanghai, _shenzheng))
        else:
            self.response('Sorry, we can not support %s market now.' % market)
            
    def do_stock(self, stock, subject):
        if subject.lower() == 'price':
            intent = self.ask('Do you want to know the current price?')['intent']
            if intent in (u'mood_deny', u'mood_unhappy'):
                subject = self.ask('And which kind of price? open, high or low?', False)
            elif intent in (u'mood_affirm', u'mood_great'):
                subject = 'current'
            self.do_stock(stock, subject)

        elif subject.lower().endswith('price'):
            self.do_stock(stock, subject[:-5].strip())

        elif subject in ('open', 'current', 'high', 'low'):
            stock_ = self.get_stock(stock)
            if stock_ is None:
                self.response('Failed to get the %s price for unclear reasons.' % subject)
            else:
                self.response('The %s price of %s is $%s per share.' % (subject.encode('utf-8'), stock, stock_[subject]))
        
        elif subject == 'volume':
            stock_ = self.get_stock(stock)
            if stock_ is None:
                self.response('Failed to get the %s price for unclear reasons.' % subject)
            else:
                self.response('The volume of %s is %s.' % (stock, stock_['volume']))
    
        else:
            self.response("I didn't hear clearly, what do you want me to do?.")

    def do_news(self, news=None, i=0, key=None):
        if not news:
            news = self.get_news(key)
            
        self.response(news[i].Title)

        intent = self.ask(choice(RESPONSE_CHOOSE))['intent']
        if intent in (u'mood_deny', u'mood_unhappy'):
            self.do_news(news, i+1)
        if intent in (u'mood_affirm', u'mood_great'):
            self.response("News' link is %s" % news[i].Link)
        else:
            self.response('Maybe we can try another keyword?')

    def get_news(self, subject):
        text = get(NEWS_ADDR % subject).text
        soup = BeautifulSoup(text, 'html.parser')
        infos = soup.findAll(attrs={'class': 'r-info r-info2'})
        return [NEWS_FORMAT(subject, info.a.string, info.a['href']) for info in infos if info.a.string is not None]

            
    def get_stock(self, stock):
        stock_ID, market = self.get_stock_info(stock)
        try:
            data = get(STOCK_ADDR % (market, stock_ID)).text.encode('cp936').split('"')[1].split(',')
            if market in ('sh', 'sz'):
                data = {'Name': data[0],
                        'open': data[1],
                        'high': data[4],
                        'low': data[5],
                        'current': data[3],
                        'volume': data[8]}
            elif market == 'gb_':
                data = {'Name': data[0],
                        'open': data[5],
                        'high': data[6],
                        'low': data[7],
                        'current': data[1],
                        'volume': data[10]}
            elif market == 'hk':
                data = {'Name': data[1],
                        'open': data[2],
                        'high': data[4],
                        'low': data[5],
                        'current': data[6],
                        'volume': data[12]}
            elif market == 'int_':
                return data[1]
            return data
        except:
            return None

    def get_stock_info(self, stock):
        with sql.connect('data/STOCK_NUM.db') as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM stocks WHERE Name="%s"' % stock.lower())
            data = cur.fetchone()
        if data is not None:
            return data[0][1:].lower(), data[2]
        self.response("Sorry, I don't have the number of this stock.")
        return '', ''
