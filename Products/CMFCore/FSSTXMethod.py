##############################################################################
#
# Copyright (c) 2001, 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" FSSTXMethod: Filesystem methodish Structured Text document.

$Id$
"""

from AccessControl import ClassSecurityInfo
from DocumentTemplate.DT_HTML import HTML as DTML_HTML
from Globals import DTMLFile
from Globals import InitializeClass
from OFS.DTMLDocument import DTMLDocument
from StructuredText.StructuredText import HTML as STX_HTML
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate

from Products.CMFCore.DirectoryView import registerFileExtension
from Products.CMFCore.DirectoryView import registerMetaType
from Products.CMFCore.FSObject import FSObject
from Products.CMFCore.permissions import FTPAccess
from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ViewManagementScreens
from Products.CMFCore.utils import _dtmldir
from Products.CMFCore.utils import _checkConditionalGET
from Products.CMFCore.utils import _setCacheHeaders
from Products.CMFCore.utils import _ViewEmulator

_STX_TEMPLATE = 'ZPT'  # or 'DTML'

_DEFAULT_TEMPLATE_DTML = """\
<dtml-var standard_html_header>
<dtml-var cooked>
<dtml-var standard_html_footer>"""

_CUSTOMIZED_TEMPLATE_DTML = """\
<dtml-var standard_html_header>
<dtml-var stx fmt="structured-text">
<dtml-var standard_html_footer>"""

_DEFAULT_TEMPLATE_ZPT = """\
<html metal:use-macro="context/main_template/macros/master">
<body>

<metal:block metal:fill-slot="body"
><div tal:replace="structure options/cooked">
COOKED TEXT HERE
</div>
</metal:block>

</body>
</html>
"""

_CUSTOMIZED_TEMPLATE_ZPT = """\
<html metal:use-macro="context/main_template/macros/master">
<body>

<metal:block metal:fill-slot="body"
><div tal:define="std modules/Products/PythonScripts/standard;
                  stx nocall:std/structured_text;"
      tal:replace="structure python:stx(template.stx)">
COOKED TEXT HERE
</div>
</metal:block>

</body>
</html>
"""

class FSSTXMethod(FSObject):
    """ A chunk of StructuredText, rendered as a skin method of a CMF site.
    """
    meta_type = 'Filesystem STX Method'
    _owner = None # unowned

    manage_options=({'label' : 'Customize','action' : 'manage_main'},
                    {'label' : 'View','action' : '',
                     'help' : ('OFSP' ,'DTML-DocumentOrMethod_View.stx')},
                   )

    security = ClassSecurityInfo()
    security.declareObjectProtected(View)

    security.declareProtected(ViewManagementScreens, 'manage_main')
    manage_main = DTMLFile('custstx', _dtmldir)

    #
    #   FSObject interface
    #
    def _createZODBClone(self):
        """
            Create a ZODB (editable) equivalent of this object.
        """
        if _STX_TEMPLATE == 'DTML':
            target = DTMLDocument(_CUSTOMIZED_TEMPLATE_DTML,
                                  __name__=self.getId())
        elif _STX_TEMPLATE == 'ZPT':
            target = ZopePageTemplate(self.getId(), _CUSTOMIZED_TEMPLATE_ZPT)

        target._setProperty('stx', self.raw, 'text')
        return target

    def _readFile(self, reparse):
        """Read the data from the filesystem.
        """
        file = open(self._filepath, 'r') # not 'rb', as this is a text file!
        try:
            data = file.read()
        finally:
            file.close()
        self.raw = data

        if reparse:
            self.cook()

    #
    #   "Wesleyan" interface (we need to be "methodish").
    #
    class func_code:
        pass

    func_code = func_code()
    func_code.co_varnames = ()
    func_code.co_argcount = 0
    func_code.__roles__ = ()

    func_defaults__roles__ = ()
    func_defaults = ()

    index_html = None   # No accidental acquisition

    default_content_type = 'text/html'

    def cook(self):
        if not hasattr(self, '_v_cooked'):
            self._v_cooked = STX_HTML(self.raw, level=1, header=0)
        return self._v_cooked

    _default_DTML_template = DTML_HTML(_DEFAULT_TEMPLATE_DTML)
    _default_ZPT_template = ZopePageTemplate('stxmethod_view',
                                             _DEFAULT_TEMPLATE_ZPT, 'text/html')

    def __call__( self, REQUEST={}, RESPONSE=None, **kw ):
        """ Return our rendered StructuredText.
        """
        self._updateFromFS()

        if RESPONSE is not None:
            RESPONSE.setHeader( 'Content-Type', 'text/html' )

        view = _ViewEmulator(self.getId()).__of__(self)
        if _checkConditionalGET(view, extra_context={}):
            return ''

        _setCacheHeaders(view, extra_context={})

        return self._render(REQUEST, RESPONSE, **kw)

    security.declarePrivate('modified')
    def modified(self):
        return self.getModTime()

    security.declarePrivate('_render')
    def _render(self, REQUEST={}, RESPONSE=None, **kw):
        """ Find the appropriate rendering template and use it to render us.
        """
        if _STX_TEMPLATE == 'DTML':
            default_template = self._default_DTML_template
        elif _STX_TEMPLATE == 'ZPT':
            default_template = self._default_ZPT_template
        else:
            raise TypeError('Invalid STX template: %s' % _STX_TEMPLATE)

        template = getattr(self, 'stxmethod_view', default_template)

        if getattr(template, 'isDocTemp', 0):
            #posargs = (self, REQUEST, RESPONSE)
            posargs = (self, REQUEST)
        else:
            posargs = ()

        kwargs = {'cooked': self.cook()}
        return template(*posargs, **kwargs)

    security.declareProtected(FTPAccess, 'manage_FTPget')
    def manage_FTPget(self):
        """ Fetch our source for delivery via FTP.
        """
        return self.raw

    security.declareProtected(ViewManagementScreens, 'PrincipiaSearchSource')
    def PrincipiaSearchSource(self):
        """ Fetch our source for indexing in a catalog.
        """
        return self.raw

    security.declareProtected(ViewManagementScreens, 'document_src')
    def document_src( self ):
        """ Fetch our source for rendering in the ZMI.
        """
        return self.raw

InitializeClass(FSSTXMethod)

registerFileExtension('stx', FSSTXMethod)
registerMetaType('STX Method', FSSTXMethod)