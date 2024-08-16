# -*- coding: utf-8 -*-
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx_tabs.tabs import CodeTabDirective, TabsDirective
from sphinxcontrib.httpexample import builders
from sphinxcontrib.httpexample import parsers
from sphinxcontrib.httpexample import utils

import os
import re


AVAILABLE_BUILDERS = {
    'curl': (builders.build_curl_command, 'bash'),
    'wget': (builders.build_wget_command, 'bash'),
    'httpie': (builders.build_httpie_command, 'bash'),
    'requests': (builders.build_requests_command, 'python'),
    'python-requests': (builders.build_requests_command, 'python'),
    'plone-javascript': (builders.build_plone_javascript_command,
                         'javascript'),
}

AVAILABLE_FIELDS = [
    'query'
]


def choose_builders(arguments):
    return [directives.choice(argument, AVAILABLE_BUILDERS)
            for argument in (arguments or [])]


class HTTPExample(TabsDirective):

    required_arguments = 0
    optional_arguments = len(AVAILABLE_BUILDERS)

    option_spec = utils.merge_dicts(CodeTabDirective.option_spec, {
        'request': directives.unchanged,
        'response': directives.unchanged,
    })

    def run(self):
        self._old_parse = self.state.nested_parse
        self.state.nested_parse = (lambda *args: self.nested_parse(args[-1]))
        result = super(HTTPExample, self).run()

        return result

    def assert_has_content(self):
        # The tabs directive wants content, but we don't need it because we generate out own.
        pass

    def nested_parse(self, node):
        node['classes'].append('http-example')

        self.state.nested_parse = self._old_parse

        config = self.state.document.settings.env.config

        # Read enabled builders; Defaults to None
        chosen_builders = choose_builders(self.arguments)

        # Enable 'http' language for http part
        self.arguments = ['http']

        # process 'query' reST fields
        if self.content:
            raw = ('\r\n'.join(self.content)).encode('utf-8')
            request = parsers.parse_request(raw)
            params, _ = request.extract_fields('query')
            params = [(p[1], p[2]) for p in params]
            new_path = utils.add_url_params(request.path, params)
            self.content[0] = ' '.join(
                [request.command, new_path, request.request_version])

        # split the request and optional response in the content.
        # The separator is two empty lines followed by a line starting with
        # 'HTTP/' or 'HTTP '
        request_content = StringList()
        request_content_no_fields = StringList()
        response_content = None
        emptylines_count = 0
        in_response = False
        is_field = r':({}) (.+): (.+)'.format('|'.join(AVAILABLE_FIELDS))
        for i, line in enumerate(self.content):
            source = self.content.source(i)
            if in_response:
                response_content.append(line, source)
            else:
                if emptylines_count >= 2 and \
                        (line.startswith('HTTP/') or line.startswith('HTTP ')):
                    in_response = True
                    response_content = StringList()
                    response_content.append(line, source)
                elif line == '':
                    emptylines_count += 1
                else:
                    request_content.extend(
                        StringList([''] * emptylines_count, source))
                    request_content.append(line, source)

                    if not re.match(is_field, line):
                        request_content_no_fields.extend(
                            StringList([''] * emptylines_count, source))
                        request_content_no_fields.append(line, source)

                    emptylines_count = 0

        # Load optional external request
        cwd = os.path.dirname(self.state.document.current_source)
        if 'request' in self.options:
            request = utils.resolve_path(self.options['request'], cwd)
            with open(request) as fp:
                request_content = request_content_no_fields = StringList(
                    list(map(str.rstrip, fp.readlines())), request)

        # Load optional external response
        if 'response' in self.options:
            response = utils.resolve_path(self.options['response'], cwd)
            with open(response) as fp:
                response_content = StringList(
                    list(map(str.rstrip, fp.readlines())), response)

        http_tab = CodeTabDirective(
            'code-tab',
            # Enable 'http' language for http part
            ['http', 'http'],
            self.options,
            # set the content to the request, stripped of the reST fields
            StringList(request_content_no_fields),
            self.lineno,
            self.content_offset,
            self.block_text,
            self.state,
            self.state_machine
        )
        node.extend(http_tab.run())
        node[-1]['classes'].append('http-example-http')

        # reset the content to just the request
        self.content = request_content

        # Append builder responses
        if request_content_no_fields:
            raw = ('\r\n'.join(request_content_no_fields)).encode('utf-8')
            for name in chosen_builders:
                request = parsers.parse_request(raw, config.httpexample_scheme)
                builder_, language = AVAILABLE_BUILDERS[name]

                # Setting plone JavaScript tab name
                name = 'JavaScript' if name == 'plone-javascript' else name

                command = builder_(request)

                content = StringList(
                    [command], request_content_no_fields.source(0))
                options = self.options.copy()
                options.pop('name', None)
                options.pop('caption', None)

                tab = CodeTabDirective(
                    'code-tab',
                    [language, name],
                    options,
                    content,
                    self.lineno,
                    self.content_offset,
                    self.block_text,
                    self.state,
                    self.state_machine
                )
                node.extend(tab.run())
                klass = 'http-example-{}'.format(name)
                node[-1]['classes'].append(klass)

        # Append optional response
        if response_content:
            options = self.options.copy()
            options.pop('name', None)
            options.pop('caption', None)

            response_tab = CodeTabDirective(
                'code-tab',
                ['http', 'response'],
                options,
                request_content,
                self.lineno,
                self.content_offset,
                self.block_text,
                self.state,
                self.state_machine
            )
            node.extend(response_tab.run())
            node[-1]['classes'].append('http-example-response')