# -*- coding: utf-8 -*-
from sphinxcontrib.httpexample.directives import HTTPExample

import os
import pkg_resources
import shutil


CSS_FILE = 'sphinxcontrib-httpexample.css'


def copy_assets(app, exception):
    if app.builder.name != 'html' or exception:
        return

    # CSS
    src = os.path.join(os.path.dirname(__file__), 'static', CSS_FILE)
    dst = os.path.join(app.builder.outdir, '_static', CSS_FILE)
    shutil.copyfile(src, dst)


def setup(app):
    app.setup_extension("sphinx_tabs.tabs")
    app.connect('build-finished', copy_assets)
    app.add_directive_to_domain('http', 'example', HTTPExample)
    app.add_css_file(CSS_FILE)
    app.add_config_value('httpexample_scheme', 'http', 'html')
    dist = pkg_resources.get_distribution('sphinxcontrib-httpexample')
    return {'version': dist.version}
