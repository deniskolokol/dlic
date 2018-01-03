
root = '/ais/gobi1/ilya/data/wiki/'

class Lang:
    def __init__(self,
                 lang_code,
                 category_spelling):
        self.lang_code = lang_code

        if category_spelling.endswith(':'):
            category_spelling = category_spelling[:-1]

        self.category_spelling = category_spelling



        

    def path(self):
        import os

        file_names = os.listdir(root + self.lang_code)
                 
        xml_fnames = [f 
                     for f in file_names
                     if f.endswith('.xml')]

        assert len(xml_fnames) == 1
        
        file_name = xml_fnames[0]


        wiki_path = root + self.lang_code + '/' + file_name


        return wiki_path


    def dir_path(self):
        return root + self.lang_code



    def is_category_title(self, title):
        return title.startswith(self.category_spelling + ':')



    def is_category_link(self, title):
        return title.startswith(self.category_spelling + ':')



    def my_lang_link(self, title):
        return title.startswith(self.lang_code + ':')



    def is_article_title(self, title):
        return ':' not in title



    def is_valid_title(self, title):
        return (self.is_category_title(title) or
                self.is_article_title(title))


    



EN = Lang('en',
          'Category')





class wiki:
    def __init__(self,
                 lang):
        self.lang = lang


    def raw_docs(self):

        articles = file(self.lang.path())
        
        article_state = 0
        end_article_state = 1
        no_article_state = 2

        state = no_article_state

        lines_of_cur_article = []

        for line in articles:


            if line.lstrip().rstrip() == '<page>':
                state = article_state

            if line.lstrip().rstrip() == '</page>':
                state = end_article_state



            if state == article_state:
                lines_of_cur_article.append(line)

            elif state == end_article_state:
                lines_of_cur_article.append(line)

                yield lines_of_cur_article
                lines_of_cur_article = []

                state = no_article_state

            elif state == no_article_state:
                pass
            


    def all_docs(self):

        for doc in self.raw_docs():

            title = self.get_title(doc)
            id = self.get_id(doc)
            body = self.get_text(doc)


            if len(body) == 0:
                continue

            if body[0].startswith('#'):
                continue 

            if self.lang.is_valid_title(title):
                #yield (int(id), title, map(process, body))
                yield (int(id), title, body)







    def get_attr(self, attr, article, expected_position):
        if len(article) > expected_position:
            candidate_line = article[expected_position]

            trimmed_line = candidate_line.lstrip().rstrip()

            line_is_good = \
                trimmed_line.startswith('<' + attr + '>') \
                and \
                trimmed_line.endswith('</' + attr + '>')
        
            if line_is_good:
                return trimmed_line[len(attr) + 2 : 
                                    - len(attr) - 3]

        raise Exception ('get_atter failed with: \narticle = %s \nattr = %s \nexpected_position = %s' %
                         (article, attr, exception))




    def get_title(self, article):
        return self.get_attr(attr = 'title', 
                             article = article,
                             expected_position = 1)


    def get_id(self, article):
        return int(self.get_attr(attr = 'id', 
                                 article = article,
                                 expected_position = 2))



    def get_text(self, article):
        ## This code seems to work, so great!

        ## Step 1: find a line that starts with <text ... >

        for (i, line) in enumerate(article):
            if line.lstrip().startswith('<text'):
                begin_text_line = i
                break


        for (i, line) in enumerate(article):
            if line.rstrip().endswith('</text>'):
                end_text_line = i
                text_exists = True
                break

            if i == begin_text_line and line.rstrip().endswith('/>'):
                end_text_line = i
                text_exists = False
                break


        if text_exists is True:

            begin_text_pos = article[begin_text_line].index('>')  + 1
            first_line = article[begin_text_line][begin_text_pos:]

            mid_lines = article[begin_text_line + 1: end_text_line]

        
            last_line = article[end_text_line].rstrip()[:-len('</text>')]



            ## If the text has a few lines in it:
            if begin_text_line < end_text_line:
                #self.get_text_stats.good_docs += 1

                return [first_line] + mid_lines + [last_line]
            


            ## If the text fits only one line:
            elif begin_text_line == end_text_line:
                #self.get_text_stats.short_docs += 1
                only_line = article[begin_text_line].rstrip()[begin_text_pos: -len('</text>')]
                return [only_line]



            ## </text> shouldn't occur before <text>
            else:
                raise Exception ("</text> detected after <text: bad")

        elif text_exists is False:
            #self.get_text_stats.empty_docs += 1
            return []



## I do not need to extract the links. That's correct. What do I need to do? 
def basic_process(line):
    line = line.replace('&lt;', '<')
    line = line.replace('&gt;', '>')
    line = line.replace('&quot;', '"')
    line = line.replace('&nbsp;', ' ')
    line = line.replace('&amp;', '&')
    line = line.replace('&mdash;', '-')
    line = line.replace('&ndash;', '-')

    return line


def eliminate(left, right, line):
    import re
    return re.sub(left + r'([^\n]*)' + right, '', line)

def eliminate_ltgt(left, right, line):
    import re
    #return re.sub(left + r'([\w \+\-\*\/\"\'\&\!\?\,\.\:\;\\]+)' + right, '', line)
    #return re.sub(left + r'([a-zA-Z0-9_ \*\+\-\,\.\:\;\?\=\"\'\$\#]+)' + right, '', line)
    return re.sub(left + r'([^[\<]+)' + right, '', line) # Note: we don't have \>, becasue we don't close the thing we're after.

def delink(line):
    import re
    #line = re.sub(r'\[\[([^\n]*)\]\]', r'\1', line)
    #line = re.sub(r'\[\[([^\|]+)\|([^\n]+)\]\]', r'\2', line)
    #line = re.sub(r'\[\[([^\n\:]+)\:([^\n\|]+)\|\]\]', r'\2', line)
    #line = re.sub(r'\[\[([^\n]+)\|\]\]', r'\1', line)

    #line = re.sub(r'\[\[([a-zA-Z0-9_ \'\":=().,!\-+]*)\]\]', r'\1', line)
    #line = re.sub(r'\[\[([a-zA-Z0-9_ \'\":=().,!\-+]*)\|\]\]', r'\1', line)
    #line = re.sub(r'\[\[([a-zA-Z0-9_ \'\":=().,!\-+]*)\|([!a-zA-Z0-9_ \'\":=().,:!+\\/\-]*)\]\]', r'\2', line)
    #line = re.sub(r'\[\[([a-zA-Z0-9_ \'\":=().,!\-+]*)\|([^\n]+)\]\]', r'\2', line)


    line = re.sub(r'\[\[([^[]|]+)\]\]', r'\1', line)
    line = re.sub(r'\[\[([^|]+)\|\]\]', r'\1', line)
    line = re.sub(r'\[\[([^|]+)\|([^\|]+)\]\]', r'\2', line)
    return line

def delink2(line):
    import re
    line = re.sub(r'\[(http|ftp)[\w.\-\;\:\~_#\&\*\?\/\"\'\\]* ([\w \-\*\"\']*)\]', r'\2', line)
    #line = re.sub(r'\[(http|ftp)[\w.\-\;\:\~_#\&\*\?\/\"\'\\]* ([^[]]*)\]', r'\2', line)

    line = re.sub(r'\[[\w.\-\;\:\~_#\&\*\?\/\"\'\\]+\]', '', line)
    return line



def process(line):
    import re
    line = basic_process(line)
    line = basic_process(line)

    line = eliminate('{{', '}}', line) 
    line = eliminate('{', '}', line)

    line = delink(line)
    line = delink2(line)

    line = line.replace('[', '')
    line = line.replace(']', '')


    line = line.replace("'''", '"')
    line = line.replace("''", '"')



    line = eliminate(r'\<\!\-\-', r'\-\-\>', line)


    line = eliminate_ltgt(r'\<ref', r'\<\/ref\>', line)
    line = eliminate_ltgt(r'\<', r'\>', line)
    line = eliminate_ltgt(r'\<math', r'\</math\>', line)
    line = eliminate_ltgt(r'\<div', r'\</div\>', line)
    line = eliminate_ltgt(r'\<syntaxthighlight', r'\</syntaxthighlight\>', line)



    ## lines without spaces are obviously defective.
    if ' ' not in line: 
        return ''

    ## Avoid lines that don't have spaces before a ':'.
    if ':' in line:
        if ' ' not in line[:line.find(':')]:
            return ''

    ## Remove weird bullet point crap. This makes the dataset less "wikipedia natural",
    ## But it's ok. We might later decide we don't want it, so we'll allow sentences that start with a '*'.
    if len(line.lstrip()) > 0:
        #if line.lstrip()[0] in set(['=', '*']): DO we allow bulleted lists and paragraph heads? No.
        #    pass

        if line.lstrip()[0].isalpha() is False:
            return ''

    if len(line.rstrip())> 0:
        if line.rstrip()[-1] in set(['|', '&']):
            return ''

    ## If a line has many spaces in succession it cannot be a valid line.
    if '  '*3 in line:
        return '' 




    if line.startswith('thumb|'):
        return ''


    return line




w = wiki(EN)





# the more the better for both of these things:
T = 200 
batch_size = 1504 

V = 100
O = 100


batch_size = 1024


T_ = 100
SKIP = 1
OFFSET = 0
T = T_ * SKIP



def load_wikipedia_first_N(num_documents):
    x = w.all_docs()
    strings = []
    orig = []
    from pylab import printf

    for i in range(num_documents):
        y = x.next()[2]

        long_ones = [line for line in y if len(line) > 200]

        ## we'll have this very long list of lines. And do it on a per-line basis.
        def filt(x): 
            return [y for y in x if y!='']
        strings.append('\n'.join(filt(map(process, long_ones))))
        #orig.extend('\n'.join(filt(long_ones)))

        ## That's good.
        if (i+1) % 1000 == 0:
            #printf ('i=%s; tot len = %s\n' % (i, sum(map(len, strings))))
            printf ('i=%s, len(strings)=%s, tot len=%s\n' % (i, len(strings), sum(map(len, strings))))

    strings = [st for st in strings if len(st) > T_ + 1]

    return strings#, orig

#raise Exception("This script has already been run. Thus wiki_letters_2G exists. So it shouldnt be run again.")

import numpy as np
import gpunumpy as g
print 'loading wikipedia.... itll take us a while.'
strings = load_wikipedia_first_N(500000)
num_strings = len(strings) 


from pylab import rand, zeros
def permute(lst):
    ans = []
    from pylab import permutation
    p = permutation(len(lst))
    for i in range(len(lst)):
        ans.append(lst[p[i]])
    return ans
def select(lst, bin_inds):
    ans = []
    assert len(lst)==len(bin_inds)
    for (elem, marker) in zip(lst, bin_inds):
        assert marker in [0,1]
        if marker:
            ans.append(elem)
    return ans
train_inds = rand(num_strings) < 0.8
train_string = '\n'.join(permute(select(strings,train_inds)))
test_string = '\n'.join(permute(select(strings,~train_inds)))


def save_it_all():
    from pylab import save
    save((train_string, test_string), 'wiki_letters_2G')

print 'will now save it all...'
save_it_all()
print 'done! the rest is easy.'

chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+.,:;?/\\!@#$%&*()"\'\n '
chars_dict = dict((c,i) for (i,c) in enumerate(chars))
chars_inv_dict = dict([(i,c) for (i,c) in enumerate(chars)] + [(len(chars), '^')])

V = len(chars) + 1 
O = len(chars) + 1 


def from_string_to_id(string):
    ans = [chars_dict.get(ch, len(chars)) for ch in string]
    return ans
def from_id_to_string(ids):

    return ''.join([chars_inv_dict[int(id)] for id in ids])

def disp_batch(batch, b):
    from pylab import find
    ans = []
    for t in range(len(batch)):
        ans.append(chars_inv_dict[int(find(batch[t][b].asarray()))])

    return ''.join(ans)


