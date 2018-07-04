# -*- coding: utf-8 -*-

import vim
from ncm2 import Ncm2Source, getLogger, Popen
from urllib.request import urlopen
from urllib.parse import urlencode
import json
import re
import subprocess
from os.path import dirname

logger = getLogger(__name__)

# token = os.getenv('GITHUB_TOKEN')


def create_request(url, token=''):
    req = url
    if token:
        req = Request(url, headers={'Authorization': 'token %s' % token})
    return req


class Source(Ncm2Source):

    repo_pat = re.compile(r'.*\b(\w+)\/$')

    def on_complete_repo(self, ctx, token):
        startccol = ctx['startccol']
        typed = ctx['typed']
        base = ctx['base']
        txt = typed[0: len(typed)-len(base)]

        # `.*` greedy match, push to the the end
        match = self.repo_pat.search(txt)
        if not match:
            logger.debug("match user string failed")
            return

        user = match.group(1)
        query = {
            'q': ctx['base'] + ' in:name user:' + user,
            'sort': 'stars',
        }

        url = 'https://api.github.com/search/repositories?' + urlencode(query)
        req = create_request(url, token)
        logger.debug("url: %s", url)

        matches = []
        with urlopen(req, timeout=10) as f:
            rsp = f.read()
            logger.debug("rsp: %s", rsp)

        rsp = json.loads(rsp.decode())
        for item in rsp['items']:
            matches.append(dict(word=item['name'], menu=item['full_name']))

        refresh = rsp['incomplete_results']
        self.complete(ctx, startccol, matches, refresh)

    repo_user_pat = re.compile('github.com[\/:](\w+)\/([\w.\-]+)\.git')

    def get_repo_user(self, cwd):
        args = ['git', 'remote', '-v']
        try:
            proc = Popen(args=args, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=cwd)
            result, errs = proc.communicate('', 10)
            result = result.decode('utf-8')
            match = self.repo_user_pat.search(result)
            if not match:
                return None, None

            return match.group(1), match.group(2)
        except Exception:
            logger.exception(
                "Failed executing _get_repo_user at cwd [%s]", cwd)
            return None, None

    def on_complete_issue(self, ctx, token, cwd):

        filepath = ctx['filepath']
        startccol = ctx['startccol']

        user, repo = self.get_repo_user(dirname(filepath))
        if not repo:
            user, repo = self.get_repo_user(cwd)

        logger.info("user [%s] repo [%s]", user, repo)
        if not repo or not user:
            return

        query = {
            'q': 'user:' + user + ' repo:' + repo,
            'sort': 'updated',
        }

        url = 'https://api.github.com/search/issues?' + urlencode(query)
        req = create_request(url, token)
        logger.debug("url: %s", url)

        matches = []
        with urlopen(req, timeout=10) as f:
            rsp = f.read()
            logger.debug("rsp: %s", rsp)

        rsp = json.loads(rsp.decode())
        for i in rsp['items']:
            matches.append(dict(word='#%s' %
                                i['number'], menu=i['title']))

        logger.debug("matches: %s", matches)
        self.complete(ctx, startccol, matches)

    link_pat = re.compile(r'.*\[((\w+)\/)?([\w.\-]+)\]\($')

    def on_complete_link(self, ctx, token):

        # `.*` greedy match, push to the the end
        typed = ctx['typed']
        base = ctx['base']
        startccol = ctx['startccol']
        txt = typed[0: len(typed)-len(base)]

        match = self.link_pat.search(txt)
        if not match:
            logger.debug("match pattern failed: %s", txt)
            return

        user = match.group(2)
        repo = match.group(3)

        query = {
            'q': repo + ' in:name',
            'sort': 'stars',
        }

        if user:
            query['q'] += ' user:' + user

        url = 'https://api.github.com/search/repositories?' + urlencode(query)
        req = create_request(url, token)
        logger.debug("url: %s", url)

        matches = []
        with urlopen(req, timeout=10) as f:
            rsp = f.read()
            logger.debug("rsp: %s", rsp)
            rsp = json.loads(rsp.decode())
            for item in rsp['items']:
                matches.append(dict(word=item['html_url']))

        logger.debug("matches: %s", matches)
        refresh = rsp['incomplete_results']
        self.complete(ctx, startccol, matches, refresh)

    def on_complete_user(self, ctx, token):
        base = ctx['base']
        query = {
            'q': base + ' in:login',
        }
        url = 'https://api.github.com/search/users?' + urlencode(query)
        req = create_request(url, token)
        logger.debug("url: %s", url)

        matches = []
        with urlopen(req, timeout=10) as f:
            rsp = f.read()
            logger.debug("rsp: %s", rsp)

        rsp = json.loads(rsp.decode())
        for item in rsp['items']:
            matches.append(item['login'])

        logger.debug("matches: %s", matches)
        refresh = rsp['incomplete_results']
        self.complete(ctx, ctx['startccol'], matches, refresh)


source = Source(vim)

on_complete_repo = source.on_complete_repo
on_complete_issue = source.on_complete_issue
on_complete_link = source.on_complete_link
on_complete_user = source.on_complete_user
