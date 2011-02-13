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
import threading
import codecs
import cPickle
import hashlib

cache_dir = '%s/.w3m/.w3m-2ch' % os.path.expanduser('~')
encode_2ch = 'cp932'
encode_w3m = 'utf-8'
bbsmenu_url = 'http://menu.2ch.net/bbsmenu.html'
bbsmenu_file = '%s/bbsmenu.html' % cache_dir
headline_url = 'http://headline.2ch.net'
headline_file = '%s/headline.html' % cache_dir
cookie_file = '%s/cookie' % cache_dir
default_name = ''
default_mail = 'sage'
script_name = os.path.basename(sys.argv[0])
cgi_script = 'cgi-bin/%s' % script_name
user_agent = 'Monazilla/1.00 (%s)' % script_name
r_thread_list_url = r'http:\/\/[^ ]*\.(?:2ch\.net|bbspink\.com)'
r_thread_url = r'http:\/\/[^ ]*\.(?:2ch\.net|bbspink\.com)\/test\/read\.cgi'

sys.stdout = codecs.lookup(encode_w3m)[-1](sys.stdout)

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
    p = re.compile(r'\.dat$')
    q = re.compile(r'\(([0-9]+)\)$')
    if url:
        def splitter(x):
            x = x.split('<>')
            key = p.sub('', x[0])
            thread_name = q.sub('', x[1])
            num = int(q.search(x[1]).group(1))
            return (key, thread_name, num)
        dir = '%s/%s' % (cache_dir, bbs)
        if not os.path.isdir(dir):
            os.mkdir(dir)
        file = '%s/subject.txt' % dir
        try:
            urllib.urlretrieve(url, file)
            f = codecs.open(file, 'r', encode_2ch)
            thread_list = unicode(f.read()).splitlines()
            f.close()
            thread_list = map(splitter, thread_list)
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
            r = re.compile(r'^[0-9]+\.dat')
            thread_list = []
            for file in [x for x in os.listdir(dir) if r.match(x)]:
                try:
                    f = codecs.open('%s/%s' % (dir, file), 'r', encode_2ch)
                    s = unicode(f.read()).splitlines()
                    f.close()
                    key = p.sub('', file)
                    thread_name = s[0].split('<>')[4]
                    thread_list.append((key, thread_name, len(s)))
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
    if new_num != None and retrieve:
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
    print '<td><a href="file:/%s?%s=%s/%s/">%s</a></td>' % (cgi_script,
            func, bbs, key, thread_name)
    print '<td nowrap align=right>(%d)</td>' % new_num
    print '<td nowrap align=right>%s</td>' % newlines
    print '<td nowrap align=right>%s</td>' % activity
    print '<td nowrap>&nbsp;%s</td>' % st
    print '</tr>'

def get_sorted_thread_list(thread_list, thread_log, sort_type, reverse):
    if sort_type == 'res':
        thread_list.sort(lambda x, y: -cmp(x[2],y[2]))
        thread_log.sort(lambda x, y: -cmp(x[2],y[2]))
    elif sort_type == 'num':
        keys = [x[0] for x in thread_log]
        tmp = [x for x in thread_list if x[0] in keys]
        tmp = [(x[0], x[1], x[2], x[2] - thread_log[keys.index(x[0])][2]) for x
                in tmp]
        tmp.sort(lambda x, y: -cmp(x[3],y[3]))
        thread_list = tmp + [x for x in thread_list if x[0] not in keys]
    elif sort_type == 'act':
        t = time.time()
        f = lambda x, y: x / (t - float(y))
        thread_list.sort(lambda x, y: -cmp(f(x[2], x[0]), f(y[2], y[0])))
    elif sort_type == 'time':
        thread_list.sort(lambda x, y: -cmp(int(x[0]),int(y[0])))
        thread_log.sort(lambda x, y: -cmp(int(x[0]),int(y[0])))
    if sort_type and reverse:
        thread_list.reverse()
        thread_log.reverse()
    return thread_list, thread_log

def print_thread_list(bbs, sort_type=None, reverse=False):
    categories, links = get_bbsmenu()
    url, board_name = get_board_url(bbs, links)
    url = '%s/subject.txt' % url
    thread_list = get_thread_list(bbs, url)
    thread_log = get_thread_list(bbs, None)
    print 'Content-Type: text/html'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '<title>%s</title>' % board_name
    print '</head>'
    print '<body>'
    print '[<a href="file:/%s?UpdateLink=on">Update Link</a>]' % cgi_script
    print '<h1>%s</h1>' % board_name
    thread_list, thread_log = get_sorted_thread_list(thread_list, thread_log,
            sort_type, reverse)
    print '<table>'
    print '<tr><td></td>'
    for type in ['res', 'num', 'act', 'time']:
        s = 'file:/%s?PrintThreadList=%s' % (cgi_script, bbs)
        print '<td nowrap align=center>'
        print '[<a href="%s&sort=%s">+</a>]' % (s, type)
        print '[<a href="%s&sort=%s&reverse=on">-</a>]' % (s, type)
        print '</td>'
    print '</tr>'
    keys = [x[0] for x in thread_log]
    for x in thread_list:
        old_num = None
        if x[0] in keys:
            old_num = thread_log[keys.index(x[0])][2]
        print_thread_header(bbs, x[0], x[1], x[2], old_num)
    print '<tr><td colspan=5><hr></td></tr>'
    print '<tr><td colspan=5><p>Delisted threads</p></td></tr>'
    keys = [x[0] for x in thread_list]
    for x in thread_log:
        if x[0] not in keys:
            print_thread_header(bbs, x[0], x[1], x[2], retrieve=False)
    print '</table>'
    print '</body>'
    print '</html>'

def apply_abone(dat, bbs, key):
    file = '%s/abone.cache' % cache_dir
    if os.path.isfile(file):
        f = open(file, 'r')
        abone_list = cPickle.load(f)
        f.close()
    else:
        abone_list = []
    abone_all = [x for x in abone_list if x[0] == '' and x[1] == '']
    abone_bbs = [x for x in abone_list if x[0] == bbs and x[1] == '']
    abone_thread = [x for x in abone_list if x[0] == bbs and x[1] == key]
    abone_list = abone_all + abone_bbs + abone_thread
    new_dat = []
    for i, str in enumerate(dat):
        v = str.split('<>')
        idx = i + 1
        for abone in abone_list:
            is_abone = True
            if abone[2] and abone[2].isdigit() and int(abone[2]) != idx:
                is_abone = False
            else:
                for j, a in enumerate(abone[3:7]):
                    if a and not a.isspace() and v[j].count(a.rstrip()) == 0:
                        is_abone = False
                        break
            if is_abone:
                str = '<><><><>'
                break
        new_dat.append(str)
    return new_dat

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
                    if k in ref:
                        ref[k].append(idx)
                    else:
                        ref[k] = [idx]
    return ref

def get_id_reference(dat):
    p = re.compile(r'ID:([^:]+)$')
    q = re.compile(r'ID:\?\?\?')
    ref = {}
    for i, str in enumerate(dat):
        v = str.split('<>')
        idx = i + 1
        m = p.search(v[2])
        if m and not q.search(v[2]):
            id = m.group(1)
            if id in ref:
                ref[id].append(idx)
            else:
                ref[id] = [idx]
    id_ref = {}
    for k, v in ref.iteritems():
        for idx in v:
            id_ref[idx] = [x for x in v if x != idx]
    return id_ref

def dat2html(dat, bbs, key):
    p = re.compile(r'<a href="?[^"]*/[0-9]+-?[0-9]*"? target="?_blank"?>'
            r'&gt;&gt;(([0-9]+)-?([0-9]*))</a>')
    q = re.compile(r'(' + r_thread_url + r'\/([^ ]*))')
    dat = apply_abone(dat, bbs, key)
    ref = get_reference(dat)
    id_ref = get_id_reference(dat)
    html = []
    for i, str in enumerate(dat):
        v = str.split('<>')
        idx = i + 1
        s = []
        s.append('<p><dt><a name=%d>%d:</a>' % (idx, idx))
        s.append('<a href="file:/%s?Abone=new&bbs=%s&key=%s&idx=%s">%s</a>' %
                (cgi_script, bbs, key, idx, v[0]))
        s.append('&nbsp; [ %s ] &nbsp;%s' % (v[1], v[2]))
        if idx in id_ref and len(id_ref[idx]) > 0:
            r = id_ref[idx]
            s.append('[<a href=#%d>%d</a>' % (r[0], r[0]))
            for x in r[1:]:
                s.append(',<a href=#%d>%d</a>' % (x, x))
            s.append(']')
        if idx in ref:
            r = ref[idx]
            s.append(' Ref:&gt;&gt;<a href=#%d>%d</a>' % (r[0], r[0]))
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
    html = dat2html(dat, bbs, key)
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
    print '<form method=POST accept-charset="%s" ' % encode_w3m
    print 'action="file:/%s">' % cgi_script
    print '<input type=submit value="Submit" name=submit>'
    print 'Name<input name=FROM value="%s" size=19>' % default_name
    print 'E-mail: <input name=mail value="%s" size=19><br>' % default_mail
    print '<textarea rows=5 cols=70 wrap=off name=MESSAGE></textarea>'
    print '<input type=hidden name=PostMsg value=on>'
    print '<input type=hidden name=bbs value=%s>' % bbs
    print '<input type=hidden name=key value=%s>' % key
    print '<input type=hidden name=time value=%d>' % int(time.time())
    print '</form><br><br>'
    print '</body></html>'
    thread_log = get_thread_list(bbs, None)
    thread_log = [x for x in thread_log if x[0] != key]
    thread_log.insert(0, (key, thread_name, new_num))
    cache_file = '%s/subject.cache' % dir
    f = open(cache_file, 'w')
    cPickle.dump(thread_log, f)
    f.close()

def delete_dat(item):
    file = '%s/%s.dat' % (cache_dir, item)
    if os.path.isfile(file):
        os.remove(file)
    bbs, key, indices = item.split('/')
    dir = '%s/%s' % (cache_dir, bbs)
    cache_file = '%s/subject.cache' % dir
    if os.path.isfile(cache_file):
        thread_log = get_thread_list(bbs, None)
        thread_log = [x for x in thread_log if x[0] != key]
        f = open(cache_file, 'w')
        cPickle.dump(thread_log, f)
        f.close()
    print 'w3m-control: BACK'

def abone2hash(abone):
    return hashlib.sha1('<>'.join(abone).encode(encode_w3m)).hexdigest()

def hash2abone(ha, abone_list):
    ha_list = [abone2hash(x) for x in abone_list]
    if ha in ha_list:
        n = ha_list.index(ha)
        abone = abone_list.pop(n)
    else:
        abone = ('', '', '', '', '', '', '')
    return abone

def query2abone(query, abone_list=None):
    if 'sha1' in query and abone_list != None:
        abone = hash2abone(query['sha1'], abone_list)
    else:
        bbs = query['bbs'] if 'bbs' in query else ''
        key = query['key'] if 'key' in query else ''
        idx = query['idx'] if 'idx' in query else ''
        f = query['FROM'] if 'FROM' in query else ''
        m = query['mail'] if 'mail' in query else ''
        id = query['id'] if 'id' in query else ''
        msg = query['MESSAGE'] if 'MESSAGE' in query else ''
        abone = (bbs, key, idx, f, m, id, msg)
    return abone

def print_abone(query):
    file = '%s/abone.cache' % cache_dir
    if os.path.isfile(file):
        f = open(file, 'r')
        abone_list = cPickle.load(f)
        f.close()
    else:
        abone_list = []
    if 'Abone' in query and query['Abone'] == 'new':
        abone = query2abone(query)
    elif 'Abone' in query and query['Abone'] == 'mod':
        abone = query2abone(query, abone_list)
    else:
        abone = ('', '', '', '', '', '', '')
    bbs, key, idx, f, m, id, msg = abone
    categories, links = get_bbsmenu()
    if bbs:
        url, board_name = get_board_url(bbs, links)
        if key:
            file = '%s/%s/%s.dat' % (cache_dir, bbs, key)
            dat, new_num, old_num = get_dat(None, file, False)
            thread_name = dat[0].split('<>')[4]
            if query['Abone'] == 'new':
                try:
                    n = int(idx) - 1
                    f, m, id, msg = tuple(dat[n].split('<>')[0:4])
                except:
                    pass
    print 'Content-Type: text/html'
    if 'Abone' not in query or query['Abone'] != 'new':
        print 'w3m-control: DELETE_PREVBUF'
    print ''
    print '<html><head>'
    print '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
    print '<title>Abone Template Setup</title></head>'
    print '<body>'
    print '<h1>Abone Template Setup</h1>'
    print '<form method=POST accept-charset="%s" ' % encode_w3m
    print 'action="file:///cgi-bin/w3m-2chpy.cgi">'
    print '<table>'
    print '<tr><td>Res:</td>'
    print '<td><input name=idx value="%s" size=70></td></tr>' % (idx if idx
            else '')
    print '<tr><td>FROM:</td>'
    print '<td><input name=FROM value="%s" size=70></td></tr>' % f
    print '<tr><td>Mail:</td>'
    print '<td><input name=mail value="%s" size=70></td></tr>' % m
    print '<tr><td>Time & ID:</td>'
    print '<td><input name=id value="%s" size=70></td></tr>' % id
    print '<tr><td>Message:</td>'
    print '<td><textarea rows=5 cols=70 wrap=off name=MESSAGE>%s' % msg
    print '</textarea>'
    print '</td></tr>'
    print '<tr><td>Scope:</td><td><select name=scope>'
    scope = [('', 'All')]
    if bbs:
        scope.append((bbs, board_name))
        if key:
            scope.append(('%s/%s' % (bbs, key), thread_name))
    scope.reverse()
    for s in scope:
        print '<option value="%s">%s' % (s[0], s[1])
    print '</select></td></tr>'
    print '<tr><td></td>'
    print '<td align=right><input type=submit value="Add" name=submit></td></tr>'
    print '</table>'
    if 'sha1' in query:
        print '<input type=hidden name=sha1 value=%s>' % query['sha1']
    print '<input type=hidden name=Abone value=add>'
    print '</form><br><br>'
    print '<table>'
    for n, abone in enumerate(abone_list):
        bbs, key, idx, f, m, id, msg = abone
        if bbs and key:
            scope = '%s/%s' % (bbs, key)
            file = '%s/%s/%s.dat' % (cache_dir, bbs, key)
            dat, new_num, old_num = get_dat(None, file, False)
            scope_name = dat[0].split('<>')[4]
        elif abone[0]:
            scope = bbs
            url, scope_name = get_board_url(bbs, links)
        else:
            scope = ''
            scope_name = 'All'
        ha = abone2hash(abone)
        print '<tr>'
        print '<td nowrap>'
        print '[<a href="file:/%s?Abone=del&sha1=%s">D</a>]' % (cgi_script, ha)
        print '[<a href="file:/%s?Abone=mod&sha1=%s">E</a>]' % (cgi_script, ha)
        print '</td>'
        print '<td nowrap>Scope:</td><td nowrap colspan=7>%s</td>' % scope_name
        print '</tr><td></td>'
        print '<td nowrap>Res:</td><td nowrap>%s</td>' % idx
        print '<td nowrap>FROM:</td><td nowrap>%s</td>' % f
        print '<td nowrap>Mail:</td><td nowrap>%s</td>' % m
        print '<td nowrap>Time & ID:</td><td nowrap>%s</td>' % id
        print '</tr><tr><td nowrap></td><td nowrap>Message:</td>'
        print '<td nowrap colspan=7>%s</td>' % msg
        print '</tr>'
    print '</table>'
    print '</body></html>'

def add_abone(query):
    bbs, key, idx, f, m, id, msg = query2abone(query)
    scope = query['scope'] if 'scope' in query else ''
    if scope:
        s = scope.split('/')
        bbs = s[0]
        key = s[1] if len(s) > 1 else ''
    abone = (bbs, key, idx, f, m, id, msg)
    file = '%s/abone.cache' % cache_dir
    if os.path.isfile(file):
        f = open(file, 'r')
        abone_list = cPickle.load(f)
        f.close()
    else:
        abone_list = []
    if 'sha1' in query:
        hash2abone(query['sha1'], abone_list)
    abone_list.insert(0, abone)
    f = open(file, 'w')
    cPickle.dump(abone_list, f)
    f.close()
    print_abone({})

def delete_abone(query):
    ha = query['sha1']
    file = '%s/abone.cache' % cache_dir
    if os.path.isfile(file):
        f = open(file, 'r')
        abone_list = cPickle.load(f)
        f.close()
    else:
        abone_list = []
    hash2abone(ha, abone_list)
    f = open(file, 'w')
    cPickle.dump(abone_list, f)
    f.close()
    print_abone({})

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


class InputHiddenParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.query = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'input':
            attrs = dict(attrs)
            if 'type' in attrs and attrs['type'] == 'hidden':
                if 'name' in attrs and 'value' in attrs:
                    name = attrs['name']
                    value = attrs['value']
                    self.query[name] = value

    def error(self, msg):
        pass


class MyCookieJar(cookielib.CookieJar):
    def __getstate__(self):
        state = self.__dict__.copy()
        del state['_cookies_lock']
        return state

    def __setstate__(self, state):
        self.__dict__ = state
        self._cookies_lock = threading.RLock()


def post_msg(query):
    query.pop('PostMsg')
    bbs = query['bbs']
    key = query['key']
    categories, links = get_bbsmenu()
    url, board_name = get_board_url(bbs, links)
    base_url = re.sub(r'\/%s' % bbs, '', url)
    referer = base_url + 'test/read.cgi/%s/%s/' % (bbs, key)
    url = base_url + 'test/bbs.cgi'
    for k, v in query.iteritems():
        query[k] = v.encode(encode_2ch)
    encoded_query = urllib.urlencode(query)
    item = '%s/%s/' % (bbs, key)
    if 'MESSAGE' not in query:
        print 'Content-Type: text/plain'
        print ''
        print 'Message is empty.'
    else:
        if os.path.isfile(cookie_file):
            f = open(cookie_file, 'r')
            cj = cPickle.load(f)
            f.close()
        else:
            cj = MyCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        req = urllib2.Request(url, encoded_query)
        req.add_header("Referer", referer)
        req.add_header("User-agent", user_agent)
        res = opener.open(req)
        html = res.read().decode(encode_2ch, 'replace')
        parser = InputHiddenParser()
        parser.feed(html)
        parser.close()
        if len(parser.query) > 0:
            for k, v in parser.query.iteritems():
                if k not in query:
                    query[k] = v.encode(encode_2ch)
            encoded_query = urllib.urlencode(query)
            req = urllib2.Request(url, encoded_query)
            req.add_header("Referer", referer)
            req.add_header("User-agent", user_agent)
            res = opener.open(req)
            html = res.read().decode(encode_2ch, 'replace')
        f = open(cookie_file, 'w')
        cj = cPickle.dump(cj, f)
        f.close()
        print_thread(item)
        print html

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
            q[k] = v[0].decode(encode_w3m, 'replace')
        query = q
        if query:
            if 'PrintBoardList' in query:
                if cgi.escape(query['PrintBoardList']) == 'reload':
                    get_bbsmenu(retrieve=True)
                print_board_list()
            elif 'PrintThreadList' in query:
                bbs = cgi.escape(query['PrintThreadList'])
                sort_type = (cgi.escape(query['sort']) if 'sort' in query else
                        None)
                reverse = (cgi.escape(query['reverse']) if 'reverse' in query
                        else None)
                print_thread_list(bbs, sort_type, reverse)
            elif 'PrintThread' in query:
                item = cgi.escape(query['PrintThread'])
                print_thread(item)
            elif 'PrintThreadLog' in query:
                item = cgi.escape(query['PrintThreadLog'])
                print_thread(item, retrieve=False)
            elif 'DeleteDat' in query:
                item = cgi.escape(query['DeleteDat'])
                delete_dat(item)
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
            elif 'Abone' in query:
                if query['Abone'] == 'new' or query['Abone'] == 'mod':
                    print_abone(query)
                elif query['Abone'] == 'add':
                    add_abone(query)
                elif query['Abone'] == 'del':
                    delete_abone(query)
    except:
        print 'Content-Type: text/plain'
        print ''
        traceback.print_exc(file=sys.stdout)

if __name__ == "__main__":
    main()

