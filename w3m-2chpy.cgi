#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import os
import traceback
import re
import cgi
import time
import HTMLParser
import urllib
import urllib2
import cookielib
import codecs
import cPickle

sys.stdout = codecs.lookup('utf_8')[-1](sys.stdout)

cache_dir = '%s/.w3m/.w3m-2ch' % os.path.expanduser('~')
encode_2ch = 'cp932'
bbsmenu_url = 'http://menu.2ch.net/bbsmenu.html'
bbsmenu_file = '%s/bbsmenu.html' % cache_dir
headline_url = 'http://headline.2ch.net'
headline_file = '%s/headline.html' % cache_dir
user_agent = 'w3m-2chpy'
script_name = os.path.basename(sys.argv[0])
cgi_script = 'cgi-bin/%s' % script_name
r_thread_list_url = r'http:\/\/[^ ]*\.(?:2ch\.net|bbspink\.com)'
r_thread_url = r'http:\/\/[^ ]*\.(?:2ch\.net|bbspink\.com)\/test\/read\.cgi'

if not os.path.isdir(cache_dir):
    os.mkdir(cache_dir)


class LinkParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.categories = []
        self.links = []
        self.category = ''
        self.atters = {}
        self.data = []
        self.flag = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.attrs = dict(attrs)
            self.flag = True
        elif tag == 'b':
            self.flag = True

    def handle_endtag(self, tag):
        if tag == 'a':
            if self.data and 'href' in self.attrs:
                url = urllib.unquote_plus(self.attrs['href'])
                name = ''.join(self.data)
                link = (url, name, self.category)
                self.links.append(link)
            self.data = []
            self.flag = False
        elif tag == 'b':
            self.category = ''.join(self.data)
            self.categories.append(self.category)
            self.flag = False

    def handle_data(self, data):
        if self.flag:
            self.data.append(data)

    def error(self, msg):
        pass

def get_bbsmenu(retrieve=False):
    try:
        if retrieve or not os.path.isfile(bbsmenu_file):
            urllib.urlretrieve(bbsmenu_url, bbsmenu_file)
        f = codecs.open(bbsmenu_file, 'r', encode_2ch)
        html = unicode(f.read())
        f.close()
        parser = LinkParser()
        parser.feed(html)
        parser.close()
        return parser.categories, parser.links
    except:
        return [],[]

def get_board_url(bbs, links):
    p = re.compile(r_thread_list_url + r'\/%s\/' % bbs)
    url, name = None, None
    for link in links:
        if p.match(link[0]):
            url= link[0]
            name = link[1]
            break
    return url, name

def print_board_list():
    categories, links = get_bbsmenu()
    print 'Content-Type: text/html'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '</head>'
    print '<body>'
    print ('[<a href="file:/%s?PrintBoardList=reload">'
            'Reload BoardList</a>]<br>' % cgi_script)
    columns = 5
    print '<table><tr><td colspan=%d>' % columns
    print 'Click to jump to each of the categories.'
    print '</td></tr><tr>'
    for idx, item in enumerate(categories):
        if (idx + 1) % columns == 0:
            print '</tr><tr>'
        print '<td><a href=#%d>%s</a></td>' % (idx, item)
    print '</tr></table><hr>'
    p = re.compile(r_thread_list_url + r'\/([^ ]*)\/')
    for idx, item in enumerate(categories):
        print '<table>'
        print '<tr><td colspan=%d>' % columns
        print '<b><a name=%d>%s</a></b></td></tr><tr>' % (idx, item)
        n = 0
        for link in [x for x in links if x[2] == item]:
            m = p.match(link[0])
            if m != None:
                n += 1
                if n % columns == 0:
                    print '</tr><tr>'
                bbs = m.group(1)
                print ('<td><a href="file:/%s?PrintThreadList=%s">%s</a>' %
                        (cgi_script, bbs, link[1]) + '</td>')
        print '</tr></table>'
    print '</body></html>'

def get_thread_list(bbs, url=None):
    if url:
        dir = '%s/%s' % (cache_dir, bbs)
        if not os.path.isdir(dir):
            os.mkdir(dir)
        file = '%s/subject.txt' % dir
        try:
            urllib.urlretrieve(url, file)
            f = codecs.open(file, 'r', encode_2ch)
            thread_list = unicode(f.read()).splitlines()
            f.close()
            thread_list = map(lambda x: tuple(x.split('<>')), thread_list)
        except:
            thread_list = []
    else:
        dir = '%s/%s' % (cache_dir, bbs)
        cache_file = '%s/subject.cache' % dir
        if os.path.isfile(cache_file):
            f = open(cache_file, 'r')
            thread_list = cPickle.load(f)
            f.close()
        else:
            p = re.compile(r'^[0-9]+\.dat')
            thread_list = []
            for file in [x for x in os.listdir(dir) if p.match(x)]:
                try:
                    f = codecs.open('%s/%s' % (dir, file), 'r', encode_2ch)
                    s = unicode(f.read()).splitlines()
                    f.close()
                    thread_name = s[0].split('<>')[4]
                    thread_list.append((file, '%s (%d)' % (thread_name,
                        len(s))))
                except:
                    pass
            if not os.path.isdir(dir):
                os.mkdir(dir)
            f = open(cache_file, 'w')
            cPickle.dump(thread_list, f)
            f.close()
    return thread_list

def print_thread_header(bbs, key, thread_name, new_num=None, old_num=None,
        retrieve=True):
    if new_num != None and old_num != None:
        newlines = '[%d]' % (new_num - old_num)
    else:
        newlines = ''
    if new_num != None:
        d = float((int(time.time()) - int(key))) / (3600 * 24)
        act = float(new_num) / d
        act = 0 if act < 0 else act
        activity = '<%.1f>' % act
    else:
        activity = ''
    if retrieve:
        func = 'PrintThread'
    else:
        func = 'PrintThreadLog'
    t = time.localtime(int(key))
    st = time.strftime('%Y/%m/%d %H:%M:%S', t)
    print '<tr>'
    print '<td nowrap><a href="file:/%s?%s=%s/%s/">%s</a></td>' % (cgi_script,
            func, bbs, key, thread_name)
    print '<td nowrap align=right>(%d)</td>' % new_num
    print '<td nowrap align=right>%s</td>' % newlines
    print '<td nowrap align=right>%s</td>' % activity
    print '<td nowrap>&nbsp;%s</td>' % st
    print '</tr>'

def print_thread_list(bbs):
    categories, links = get_bbsmenu()
    url, board_name = get_board_url(bbs, links)
    url = '%s/subject.txt' % url
    thread_list = get_thread_list(bbs, url)
    thread_log = dict(get_thread_list(bbs, None))
    print 'Content-Type: text/html'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '<title>%s</title>' % board_name
    print '</head>'
    print '<body>'
    print '[<a href="file:/%s?UpdateLink=on">Update Link</a>]' % cgi_script
    print '<h1>%s</h1>' % board_name
    print '<table>'
    p = re.compile(r'\(([0-9]+)\)$')
    q = re.compile(r'\.dat$')
    for x in thread_list:
        new_num = int(p.search(x[1]).group(1))
        old_num = None
        if x[0] in thread_log:
            old_num = int(p.search(thread_log[x[0]]).group(1))
        print_thread_header(bbs, q.sub('', x[0]), p.sub('', x[1]), new_num,
                old_num)
    print '<tr><td colspan=5><hr></td></tr>'
    print '<tr><td colspan=5><p>Delisted threads</p></td></tr>'
    files = [x[0] for x in thread_list]
    for k, v in thread_log.iteritems():
        if k not in files:
            num = int(p.search(v).group(1))
            print_thread_header(bbs, q.sub('', k), p.sub('', v), num,
                    retrieve=False)
    print '</table>'
    print '</body>'
    print '</html>'

def get_reference(dat):
    p = re.compile(r'([0-9]+)-?([0-9]*)')
    ref = {}
    for i, str in enumerate(dat):
        v = str.split('<>')
        idx = i + 1
        s = v[3].split('&gt;&gt;')
        for x in s[1:]:
            m = p.match(x)
            if m:
                start = int(m.group(1))
                if m.group(2):
                    stop = int(m.group(2)) + 1
                else:
                    stop = start + 1
                for k in xrange(start, stop):
                    if k not in ref:
                        ref[k] = [idx]
                    else:
                        ref[k].append(idx)
    return ref

def dat2html(dat):
    p = re.compile(r'<a href="?[^"]*/[0-9]+-?[0-9]*"? target="?_blank"?>'
            r'&gt;&gt;(([0-9]+)-?([0-9]*))</a>')
    q = re.compile(r'(' + r_thread_url + r'\/([^ ]*))')
    ref = get_reference(dat)
    html = []
    for i, str in enumerate(dat):
        v = str.split('<>')
        idx = i + 1
        s = []
        s.append('<p><dt><a name=%d>%d:</a>' % (idx, idx))
        s.append('<a href="mailto:%s">%s</a>' % (v[1], v[0]))
        s.append('&nbsp; [ %s ] &nbsp;%s' % (v[1], v[2]))
        if idx in ref:
            r = ref[idx]
            s.append('Ref:&gt;&gt;<a href=#%d>%d</a>' % (r[0], r[0]))
            for x in r[1:]:
                s.append(',<a href=#%d>%d</a>' % (x, x))
        s.append('</dt><dd>')
        msg = p.sub(r'<a href=#\2>&gt;&gt;\1</a>', v[3])
        msg = (q.sub(r'[<a href="file:/%s?PrintThread=\2">*</a>]\1' %
            cgi_script, msg))
        s.append('%s</dd></p>' % msg)
        html.append(''.join(s))
    return html

def get_dat(url, file, retrieve):
    try:
        f = codecs.open(file, 'r', encode_2ch)
        dat = unicode(f.read()).splitlines()
        offset = f.tell()
        f.close()
        old_num = len(dat)
    except:
        dat, offset = [], 0
        old_num = 0
    if retrieve:
        try:
            urllib.urlretrieve(url, file)
            f = codecs.open(file, 'r', encode_2ch)
            if unicode(f.readline()).count('<>') != 4:
                raise
            f.seek(0, 2)
            if f.tell() < offset:
                f.seek(0)
                dat = unicode(f.read()).splitlines()
            else:
                f.seek(offset)
                new_dat = unicode(f.read()).splitlines()
                dat.extend(new_dat)
            f.close()
        except:
            f = codecs.open(file, 'w', encode_2ch)
            f.write('\n'.join(dat))
            f.close()
    new_num = len(dat)
    return dat, new_num, old_num

def print_thread(item, retrieve=True):
    bbs, key, indices = item.split('/')
    categories, links = get_bbsmenu()
    url, board_name = get_board_url(bbs, links)
    orig_url = re.sub(r'\/%s' % bbs, '', url) + 'test/read.cgi/%s/%s/' % (bbs,
            key)
    dir = '%s/%s' % (cache_dir, bbs)
    if not os.path.isdir(dir):
        os.mkdir(dir)
    file = '%s/%s.dat' % (dir, key)
    dat, new_num, old_num = get_dat('%s/dat/%s.dat' % (url, key), file,
            retrieve)
    if new_num == 0 or dat[0].count('<>') != 4:
        print 'Content-Type: text/html'
        print 'w3m-control: MARK_URL'
        print ''
        print '<html><body>'
        print 'Cannot find dat file.<br>'
        print orig_url
        print '</body></html>'
        return
    thread_name = dat[0].split('<>')[4]
    print 'Content-Type: text/html'
    if indices:
        m = re.match(r'^([0-9]+)', indices)
        n = re.match(r'^l([0-9]+)', indices)
        if m != None:
            print 'w3m-control: GOTO #%d' % int(m.group(1))
        elif n != None:
            print 'w3m-control: GOTO #%d' % (new_num - int(n.group(1)))
        else:
            print 'w3m-control: GOTO #1'
    elif old_num != new_num:
        print 'w3m-control: GOTO #%d' % (old_num + 1)
    else:
        print 'w3m-control: GOTO #%d' % new_num
    print 'w3m-control: DELETE_PREVBUF'
    print 'w3m-control: MARK_URL'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '<title>%s</title></head>' % thread_name
    print '<body>'
    thread_menu = ('[<a href="file:/%s?PrintThreadList=%s">Thread list</a>]' %
            (cgi_script, bbs))
    thread_menu += ('[<a href="file:/%s?DeleteDat=%s/%s/">Delete dat</a>]' %
            (cgi_script, bbs, key))
    print thread_menu
    print '<br><hr>'
    print '<h1>%s</h1>' % thread_name
    print '<a href="%s">%s</a><br>' % (orig_url, orig_url)
    print '<dl>'
    html = dat2html(dat)
    for i,s in enumerate(html):
        if old_num != new_num and i == old_num:
            print '<p><table width=50% border=5><tr align=center><td>'
            print '<a name=new>*</a> Newly arriving messages'
            print '</td></tr></table></p>'
        print s
    print '</dl><hr>'
    print '<a href=#new>Newly arriving messages</a>'
    print '<hr>'
    print thread_menu
    print '<br><br>'
    print '<form method=POST accept-charset="cp932" '
    print 'action="file:///cgi-bin/w3m-2chpy.cgi">'
    print '<input type=submit value="Submit" name=submit>'
    print 'Name<input name=FROM size=19>'
    print 'E-mail: <input name=mail value="sage" size=19><br>'
    print '<textarea rows=5 cols=70 wrap=off name=MESSAGE></textarea>'
    print '<input type=hidden name=PostMsg value=on>'
    print '<input type=hidden name=kuno value=ichi>'
    print '<input type=hidden name=hana value=mogera>'
    print '<input type=hidden name=bbs value=%s>' % bbs
    print '<input type=hidden name=key value=%s>' % key
    print '<input type=hidden name=time value=%d>' % int(time.time())
    print '</form><br><br>'
    print '</body></html>'
    filename = '%s.dat' % key
    thread_log = get_thread_list(bbs, None)
    for n, x in enumerate(thread_log):
        if x[0] == filename:
            thread_log.pop(n)
    thread_log.insert(0, (filename, '%s (%d)' % (thread_name, new_num)))
    cache_file = '%s/subject.cache' % dir
    f = open(cache_file, 'w')
    cPickle.dump(thread_log, f)
    f.close()

def delete_datfile(item):
    file = '%s/%s.dat' % (cache_dir, item)
    if os.path.isfile(file):
        os.remove(file)
    bbs, key, indices = item.split('/')
    dir = '%s/%s' % (cache_dir, bbs)
    cache_file = '%s/subject.cache' % dir
    if os.path.isfile(cache_file):
        filename = '%s.dat' % key
        thread_log = get_thread_list(bbs, None)
        for n, x in enumerate(thread_log):
            if x[0] == filename:
                thread_log.pop(n)
        f = open(cache_file, 'w')
        cPickle.dump(thread_log, f)
        f.close()
    print 'w3m-control: BACK'

def print_headline(type='news'):
    if type == 'news':
        url = '%s/bbynews/' % headline_url
    elif type == 'live':
        url = '%s/bbylive/' % headline_url
    try:
        urllib.urlretrieve(url, headline_file)
        f = codecs.open(headline_file, 'r', encode_2ch)
        html = unicode(f.read())
        f.close()
    except:
        print 'w3m-control: GOTO %s' % url
        print 'w3m-control: DELETE_PREVBUF'
        return
    p = re.compile(r'^(\t|<)')
    q = re.compile(r'(.*)<a href=' + r_thread_url + r'\/([^ ]*)>(.*)')
    print 'Content-Type: text/html'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '</head>'
    print '<body>'
    print '[<a href="file:/%s?UpdateLink=on">Update Link</a>]<br>' % cgi_script
    print '<table>'
    for line in html.splitlines():
        if not p.match(line):
            m = q.match(line)
            if (m != None):
                time = m.group(1)
                item = m.group(2)
                title = m.group(3)
                print '<tr>'
                print '<td nowrap>%s</td>' % time
                print ('<td nowrap><a href="file:/%s?PrintThread=%s">' %
                        (cgi_script, item))
                print '%s</a><td>' % title
                print '</tr>'
    print '</table>'
    print '</body></html>'

def update_link():
    urllib.urlretrieve(bbsmenu_url, bbsmenu_file)
    print 'w3m-control: BACK'

def post_msg(query):
    query.pop('PostMsg')
    bbs = query['bbs']
    key = query['key']
    categories, links = get_bbsmenu()
    url, board_name = get_board_url(bbs, links)
    base_url = re.sub(r'\/%s' % bbs, '', url)
    referer = base_url + 'test/read.cgi/%s/%s/' % (bbs, key)
    url = base_url + 'test/bbs.cgi'
    encoded_query = urllib.urlencode(query)
    item = '%s/%s/' % (bbs, key)
    if 'MESSAGE' not in query:
        print 'Content-Type: text/plain'
        print ''
        print 'Message is empty.'
    else:
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(base_url) # get cookie
        req.add_header("Referer", referer)
        req.add_header("User-agent", user_agent)
        res = opener.open(req)
        #print 'Content-Type: text/html'                # Debug
        #print ''                                       # Debug
        #print res.read().decode('cp932', 'replace')    # Debug
        req = urllib2.Request(url, encoded_query)
        req.add_header("Referer", referer)
        req.add_header("User-agent", user_agent)
        res = opener.open(req)
        #print res.read().decode('cp932', 'replace')    # Debug
        print_thread(item)

def main():
    try:
        if 'QUERY_STRING' in os.environ:
            query = cgi.parse_qs(os.environ['QUERY_STRING'])
        elif 'CONTENT_LENGTH' in os.environ:
            content_length = int(os.environ['CONTENT_LENGTH'])
            query = cgi.parse_qs(sys.stdin.read(content_length))
        else:
            query = {}
        q = {}
        for k, v in query.iteritems():
            q[k] = v[0]
        query = q
        if query:
            if 'PrintBoardList' in query:
                if cgi.escape(query['PrintBoardList']) == 'reload':
                    get_bbsmenu(retrieve=True)
                print_board_list()
            elif 'PrintThreadList' in query:
                bbs = cgi.escape(query['PrintThreadList'])
                print_thread_list(bbs)
            elif 'PrintThread' in query:
                item = cgi.escape(query['PrintThread'])
                print_thread(item)
            elif 'PrintThreadLog' in query:
                item = cgi.escape(query['PrintThreadLog'])
                print_thread(item, retrieve=False)
            elif 'DeleteDat' in query:
                item = cgi.escape(query['DeleteDat'])
                delete_datfile(item)
            elif 'PrintHeadLine' in query:
                type = cgi.escape(query['PrintHeadLine'])
                if type == 'NEWS':
                    print_headline()
                elif type == 'LIVE':
                    print_headline(type='live')
            elif 'UpdateLink' in query:
                update_link()
            elif 'PostMsg' in query:
                post_msg(query)
    except:
        print 'Content-Type: text/plain'
        print ''
        traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
    main()

